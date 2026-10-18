"""AWS wiring tests use mocks; live service results are recorded separately."""
import json
from io import BytesIO
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from farmsync.ai.engine import AIAssistantEngine
from farmsync.spatial.amazon_location import AmazonLocationServiceEngine


def engine():
    eng = AIAssistantEngine.__new__(AIAssistantEngine)
    eng.region = "ap-south-1"
    eng.bedrock_model_id = "mistral.ministral-3-3b-instruct"
    eng.bedrock_client = MagicMock()
    eng.last_bedrock_check = None
    return eng


def test_constructed_client_is_not_verified_connection():
    status = engine().get_status()
    assert status["bedrock_client_ready"]
    assert status["connection_status"] == "UNVERIFIED"
    assert status["connection_verified"] is False
    assert status["latency_benchmark"] is None


def test_successful_converse_records_verified_state():
    eng = engine()
    eng.bedrock_client.converse.return_value = {"output": {"message": {"content": [{"text": "OK"}]}}}
    assert eng._invoke_bedrock_converse("system", "question")["text"] == "OK"
    assert eng.get_status()["connection_verified"] is True


@pytest.mark.parametrize("code", ["UnrecognizedClientException", "AccessDeniedException", "ThrottlingException"])
def test_auth_and_quota_errors_do_not_retry_other_api(code):
    eng = engine()
    eng.bedrock_client.converse.side_effect = ClientError({"Error": {"Code": code}}, "Converse")
    with pytest.raises(ClientError):
        eng._invoke_bedrock_converse("system", "question")
    eng.bedrock_client.invoke_model.assert_not_called()
    assert eng.get_status()["last_live_check"]["error_code"] == code
    assert eng.get_status()["connection_verified"] is False


def test_ministral_legacy_request_uses_messages_schema():
    eng = engine()
    eng.bedrock_client.invoke_model.return_value = {"body": BytesIO(json.dumps({"choices": [{"message": {"content": "OK"}}]}).encode())}
    result = eng._invoke_bedrock_legacy("system", "question", 16, 0)
    request = eng.bedrock_client.invoke_model.call_args.kwargs
    body = json.loads(request["body"])
    assert "messages" in body
    assert "prompt" not in body
    assert request["contentType"] == "application/json"
    assert result["text"] == "OK"


def test_selected_model_updates_runtime(monkeypatch):
    eng = engine()
    monkeypatch.setattr(eng, "_init_bedrock_client", lambda: None)
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION", "BEDROCK_MODEL_ID"):
        monkeypatch.setenv(name, "test")
    eng.configure_aws("test", "test", model_id="mistral.ministral-3-8b-instruct")
    assert eng.bedrock_model_id == "mistral.ministral-3-8b-instruct"


def test_request_model_is_isolated_and_preserved_in_legacy_fallback():
    eng = engine()
    default_model = eng.bedrock_model_id
    selected = "mistral.ministral-3-8b-instruct"
    eng.bedrock_client.converse.return_value = {"output": {"message": {"content": [{"text": "OK"}]}}}
    eng._invoke_bedrock_converse("system", "question", model_id=selected)
    assert eng.bedrock_client.converse.call_args.kwargs["modelId"] == selected
    assert eng.bedrock_model_id == default_model
    eng._invoke_bedrock_converse("system", "question")
    assert eng.bedrock_client.converse.call_args.kwargs["modelId"] == default_model

    eng.bedrock_client.converse.side_effect = ClientError({"Error": {"Code": "ValidationException"}}, "Converse")
    eng.bedrock_client.invoke_model.return_value = {"body": BytesIO(json.dumps({"choices": [{"message": {"content": "OK"}}]}).encode())}
    eng._invoke_bedrock_converse("system", "question", model_id=selected)
    assert eng.bedrock_client.invoke_model.call_args.kwargs["modelId"] == selected
    assert eng.bedrock_model_id == default_model


def test_unapproved_request_model_is_rejected_before_inference():
    eng = engine()
    with pytest.raises(ValueError, match="approved"):
        eng._invoke_bedrock_converse("system", "question", model_id="unapproved-model")
    eng.bedrock_client.converse.assert_not_called()


def test_location_client_construction_is_not_connectivity():
    eng = AmazonLocationServiceEngine.__new__(AmazonLocationServiceEngine)
    eng.client = MagicMock()
    eng.region = "ap-south-1"
    eng.place_index = "test"
    eng.route_calculator = "test"
    eng.geofence_collection = "test"
    eng.last_live_checks = {}
    assert eng.get_status()["connected"] is False
    eng.last_live_checks = {"geocoding": {"success": True}, "routing": {"success": True}}
    assert eng.get_status()["connected"] is True
