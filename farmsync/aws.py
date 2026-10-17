"""AWS access aligned with the organizer's Task 1 access guide.

All clients use Mumbai, verified TLS, bounded attempts and the SDK credential
chain (temporary environment credentials, SSO profiles or deployment roles).
"""
from datetime import datetime, timezone
from functools import lru_cache
import json
import os
from pathlib import Path
import ssl
import tempfile

import boto3
from botocore.config import Config
from botocore.httpsession import get_cert_path

REGION = "ap-south-1"
TEXT_MODEL = "mistral.ministral-3-3b-instruct"
TEACHER_MODEL = "mistral.ministral-3-8b-instruct"
EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
MULTIMODAL_EMBEDDING_MODEL = "amazon.titan-embed-image-v1"
APPROVED_MODELS = frozenset({TEXT_MODEL, TEACHER_MODEL, EMBEDDING_MODEL, MULTIMODAL_EMBEDDING_MODEL})
CORE_SERVICES = frozenset({"s3", "lambda", "apigateway", "dynamodb", "logs"})


def offline():
    return os.getenv("FARMSYNC_OFFLINE", "false").lower() == "true"


def validate_region(region):
    if region != REGION:
        raise ValueError("The challenge permits AWS workloads only in ap-south-1 (Mumbai).")
    return region


def validate_model(model_id, *, text_only=False):
    allowed = {TEXT_MODEL, TEACHER_MODEL} if text_only else APPROVED_MODELS
    if model_id not in allowed:
        raise ValueError("Model is not in the organizer's approved Task 1 model list; cross-region profiles are not enabled.")
    return model_id


@lru_cache(maxsize=1)
def system_ca_bundle():
    """Use existing Windows trust, without installing roots or disabling TLS."""
    if os.name != "nt":
        return True
    certificates = ssl.create_default_context().get_ca_certs(binary_form=True)
    pem = Path(get_cert_path(True)).read_text(encoding="ascii")
    pem += "\n" + "".join(ssl.DER_cert_to_PEM_cert(cert) for cert in certificates)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", prefix="farmsync-ca-", encoding="ascii", delete=False) as handle:
        handle.write(pem)
        return handle.name


def create_client(service, region=None):
    region = validate_region(region or os.getenv("AWS_DEFAULT_REGION", REGION))
    if offline():
        return None
    if service == "location" and os.getenv("FARMSYNC_AMAZON_LOCATION_ENABLED", "false").lower() != "true":
        return None
    if service not in CORE_SERVICES | {"bedrock-runtime", "sts", "location"}:
        raise ValueError("AWS service is not configured for this application.")
    profile = os.getenv("FARMSYNC_AWS_PROFILE") or os.getenv("AWS_PROFILE") or None
    session_options = {"profile_name": profile, "region_name": region}
    if service == "location":
        location_profile = os.getenv("FARMSYNC_LOCATION_AWS_PROFILE")
        location_keys = {
            "aws_access_key_id": os.getenv("LOCATION_AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": os.getenv("LOCATION_AWS_SECRET_ACCESS_KEY"),
            "aws_session_token": os.getenv("LOCATION_AWS_SESSION_TOKEN"),
        }
        if location_profile:
            session_options["profile_name"] = location_profile
        elif any(location_keys.values()):
            if not all(location_keys.values()):
                raise ValueError("All three Location role credential values must be configured together.")
            session_options.update(location_keys)
            session_options["profile_name"] = None
    session = boto3.Session(**session_options)
    # Resolve the chain; an SSO/profile session bypasses stale environment keys.
    if session.get_credentials() is None:
        return None
    return session.client(
        service,
        region_name=region,
        verify=os.getenv("AWS_CA_BUNDLE") or system_ca_bundle(),
        config=Config(connect_timeout=5, read_timeout=30, retries={"total_max_attempts": 1}),
    )


def safe_error(exc):
    response = getattr(exc, "response", {})
    return response.get("Error", {}).get("Code") or type(exc).__name__


def check_approved_services():
    """A small explicit live probe; no creation, IAM changes or role enumeration."""
    import io
    from PIL import Image
    result = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "region": REGION, "checks": {}}
    checks = result["checks"]
    if offline():
        checks["credentials"] = {"status": "DISABLED", "reason": "FARMSYNC_OFFLINE is enabled"}
        result["all_passed"] = False
        return result
    try:
        sts = create_client("sts")
        if sts is None:
            raise RuntimeError("No AWS credential provider is available")
        sts.get_caller_identity()
        checks["credentials"] = {"status": "PASS"}
    except Exception as exc:
        checks["credentials"] = {"status": "FAIL", "error_code": safe_error(exc)}
        for name in ("text_3b", "vision_8b", "text_embeddings", "multimodal_embeddings"):
            checks[name] = {"status": "NOT_RUN", "reason": "Credentials must pass first"}
        result["all_passed"] = False
        return result
    runtime = create_client("bedrock-runtime")
    picture = io.BytesIO()
    Image.new("RGB", (32, 32), "green").save(picture, format="JPEG")
    image_bytes = picture.getvalue()
    def converse(model, content):
        response = runtime.converse(modelId=model, messages=[{"role": "user", "content": content}], inferenceConfig={"maxTokens": 16, "temperature": 0})
        if not any(block.get("text", "").strip() for block in response.get("output", {}).get("message", {}).get("content", [])):
            raise ValueError("No text in the model response")
    def embedding(model, body, dimensions):
        response = runtime.invoke_model(modelId=model, body=json.dumps(body), contentType="application/json", accept="application/json")
        data = json.loads(response["body"].read())
        vector = data.get("embedding", [])
        if len(vector) != dimensions or not all(isinstance(v, (float, int)) for v in vector):
            raise ValueError("Invalid embedding response")
    import base64
    operations = {
        "text_3b": lambda: converse(TEXT_MODEL, [{"text": "Reply OK."}]),
        "vision_8b": lambda: converse(TEACHER_MODEL, [{"image": {"format": "jpeg", "source": {"bytes": image_bytes}}}, {"text": "Name the dominant color."}]),
        "text_embeddings": lambda: embedding(EMBEDDING_MODEL, {"inputText": "Coconut crop advisory", "dimensions": 256, "normalize": True}, 256),
        "multimodal_embeddings": lambda: embedding(MULTIMODAL_EMBEDDING_MODEL, {"inputImage": base64.b64encode(image_bytes).decode(), "embeddingConfig": {"outputEmbeddingLength": 256}}, 256),
    }
    for name, operation in operations.items():
        try:
            operation()
            checks[name] = {"status": "PASS"}
        except Exception as exc:
            checks[name] = {"status": "FAIL", "error_code": safe_error(exc)}
    result["all_passed"] = all(check["status"] == "PASS" for check in checks.values())
    return result
