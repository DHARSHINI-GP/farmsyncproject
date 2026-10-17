"""Organizer policy, credential chain and approved multimodal request checks."""
from io import BytesIO
import json
from unittest.mock import MagicMock

import numpy as np
from PIL import Image
import pytest

from farmsync import aws
from farmsync.knowledge.advisory import AgronomyKnowledgeEngine
from farmsync.vision.classifier import CropVisionPipeline


@pytest.mark.parametrize("region", ["us-east-1", "ap-southeast-1", ""])
def test_only_mumbai_is_permitted(region):
    with pytest.raises(ValueError):
        aws.validate_region(region)


@pytest.mark.parametrize("model", ["anthropic.claude-3-5-sonnet-20241022-v2:0", "us.any.model", "amazon.titan-text-express-v1"])
def test_only_organizer_models_are_permitted(model):
    with pytest.raises(ValueError):
        aws.validate_model(model)


def test_profile_and_tls_are_used_consistently(monkeypatch):
    monkeypatch.setenv("FARMSYNC_OFFLINE", "false")
    monkeypatch.setenv("FARMSYNC_AWS_PROFILE", "builder-session")
    monkeypatch.delenv("AWS_CA_BUNDLE", raising=False)
    session = MagicMock()
    factory = MagicMock(return_value=session)
    monkeypatch.setattr(aws.boto3, "Session", factory)
    monkeypatch.setattr(aws, "system_ca_bundle", lambda: "trusted-system-ca.pem")
    aws.create_client("bedrock-runtime", aws.REGION)
    factory.assert_called_once_with(profile_name="builder-session", region_name=aws.REGION)
    assert session.client.call_args.kwargs["verify"] == "trusted-system-ca.pem"
    assert session.client.call_args.kwargs["config"].retries["total_max_attempts"] == 1


def test_location_is_not_part_of_default_task_one_access(monkeypatch):
    monkeypatch.setenv("FARMSYNC_OFFLINE", "false")
    monkeypatch.delenv("FARMSYNC_AMAZON_LOCATION_ENABLED", raising=False)
    assert aws.create_client("location") is None


def test_rejected_credentials_stop_paid_model_checks(monkeypatch):
    monkeypatch.setenv("FARMSYNC_OFFLINE", "false")
    sts = MagicMock()
    sts.get_caller_identity.side_effect = RuntimeError("unavailable")
    factory = MagicMock(return_value=sts)
    monkeypatch.setattr(aws, "create_client", factory)
    result = aws.check_approved_services()
    assert result["all_passed"] is False
    assert result["checks"]["text_3b"]["status"] == "NOT_RUN"
    factory.assert_called_once_with("sts")


def test_location_role_credentials_do_not_replace_ai_session(monkeypatch):
    monkeypatch.setenv("FARMSYNC_OFFLINE", "false")
    monkeypatch.setenv("FARMSYNC_AMAZON_LOCATION_ENABLED", "true")
    monkeypatch.setenv("FARMSYNC_AWS_PROFILE", "ai-session")
    monkeypatch.delenv("FARMSYNC_LOCATION_AWS_PROFILE", raising=False)
    for key, value in [("ACCESS_KEY_ID", "location-key"), ("SECRET_ACCESS_KEY", "location-secret"), ("SESSION_TOKEN", "location-token")]:
        monkeypatch.setenv("LOCATION_AWS_" + key, value)
    factory = MagicMock()
    monkeypatch.setattr(aws.boto3, "Session", factory)
    monkeypatch.setattr(aws, "system_ca_bundle", lambda: True)
    aws.create_client("location")
    assert factory.call_args.kwargs["aws_access_key_id"] == "location-key"
    assert factory.call_args.kwargs["profile_name"] is None
    aws.create_client("bedrock-runtime")
    assert factory.call_args.kwargs == {"profile_name": "ai-session", "region_name": aws.REGION}


def test_incomplete_location_role_session_is_rejected(monkeypatch):
    monkeypatch.setenv("FARMSYNC_OFFLINE", "false")
    monkeypatch.setenv("FARMSYNC_AMAZON_LOCATION_ENABLED", "true")
    monkeypatch.delenv("FARMSYNC_LOCATION_AWS_PROFILE", raising=False)
    monkeypatch.setenv("LOCATION_AWS_ACCESS_KEY_ID", "location-key")
    monkeypatch.delenv("LOCATION_AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("LOCATION_AWS_SESSION_TOKEN", raising=False)
    with pytest.raises(ValueError, match="All three Location"):
        aws.create_client("location")


def test_teacher_uses_approved_converse_image_format(tmp_path):
    pipeline = CropVisionPipeline.__new__(CropVisionPipeline)
    pipeline.bedrock_client = MagicMock()
    pipeline.bedrock_model_id = aws.TEACHER_MODEL
    pipeline.crop_classes = ["Coconut"]
    pipeline.stage_classes = ["full_growth"]
    answer = {"crop": "Coconut", "growth_stage": "full_growth", "confidence": .91}
    pipeline.bedrock_client.converse.return_value = {"output": {"message": {"content": [{"text": json.dumps(answer)}]}}}
    photo = tmp_path / "sample.png"
    Image.new("RGB", (32, 32), "green").save(photo)
    result = pipeline._invoke_bedrock_teacher_vlm(str(photo), "Coconut")
    assert result["success"] is True
    request = pipeline.bedrock_client.converse.call_args.kwargs
    assert request["modelId"] == aws.TEACHER_MODEL
    assert request["messages"][0]["content"][0]["image"]["source"]["bytes"].startswith(b"\xff\xd8")
    pipeline.bedrock_client.invoke_model.assert_not_called()


def test_titan_embeddings_have_consistent_dimension_and_cache():
    engine = AgronomyKnowledgeEngine.__new__(AgronomyKnowledgeEngine)
    engine.bedrock_client = MagicMock()
    engine.embedding_cache = {}
    engine.bedrock_client.invoke_model.return_value = {"body": BytesIO(json.dumps({"embedding": [1.] * 256}).encode())}
    vectors = engine._encode_text(["coconut", "coconut"])
    assert vectors.shape == (2, 256)
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1)
    engine.bedrock_client.invoke_model.assert_called_once()
    assert engine.bedrock_client.invoke_model.call_args.kwargs["modelId"] == aws.EMBEDDING_MODEL
