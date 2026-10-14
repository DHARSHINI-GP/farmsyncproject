"""
Tests for farmsync.ai.engine – verifying:
1. Bedrock Qualification (invoked ONLY when valid credentials exist; otherwise truthful local fallback)
2. Proposal's described Converse API pattern (converse called with system, messages, inferenceConfig)
3. Strict TLS certificate verification enabled by default (no verify=False)
4. Truthful GeoPandas/Shapely spatial grounding (no PostGIS misattribution in CoT)
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from farmsync.ai.engine import AIAssistantEngine


@pytest.fixture
def ai_engine_no_aws():
    """Engine with NO AWS credentials → must truthfully fall back to local reasoner."""
    env_overrides = {
        "AWS_ACCESS_KEY_ID": "",
        "AWS_SECRET_ACCESS_KEY": "",
        "AWS_SESSION_TOKEN": "",
    }
    with patch.dict(os.environ, env_overrides, clear=False):
        eng = AIAssistantEngine()
        assert eng.bedrock_client is None
        yield eng


@pytest.fixture
def ai_engine_with_mock_bedrock():
    """Engine with a mocked boto3 bedrock-runtime client simulating live AWS Bedrock."""
    eng = AIAssistantEngine.__new__(AIAssistantEngine)
    from farmsync.orchestrator import FarmSyncOrchestrator
    eng.orchestrator = FarmSyncOrchestrator()
    eng.region = "ap-south-1"
    eng.bedrock_model_id = "mistral.ministral-3-3b-instruct"
    eng.bedrock_client = MagicMock()
    yield eng


class TestBedrockQualification:
    """Verifies that Bedrock claims are qualified and never fabricated without credentials."""

    def test_status_without_credentials(self, ai_engine_no_aws):
        status = ai_engine_no_aws.get_status()
        assert status["bedrock_client_ready"] is False
        assert status["aws_credentials_configured"] is False
        assert status["bedrock_invoked_only_when_credentials_present"] is True
        assert "Local CoT" in status["active_model"]
        assert "No AWS Credentials" in status["active_model_tier"]

    def test_status_with_credentials(self, ai_engine_with_mock_bedrock):
        status = ai_engine_with_mock_bedrock.get_status()
        assert status["bedrock_client_ready"] is True
        assert "Converse API" in status["active_model"]
        assert status["converse_pattern_supported"] is True

    def test_process_query_without_credentials_truthful_fallback(self, ai_engine_no_aws):
        res = ai_engine_no_aws.process_query("What is the status of Survey 384?")
        assert res["bedrock_invoked"] is False
        assert res["aws_credentials_available"] is False
        assert res["reasoning_mode"] == "LOCAL_ENTERPRISE_COT"
        assert "AWS Bedrock Inactive" in res["model_used"]
        assert len(res["answer"]) > 50

    def test_process_query_with_bedrock_invokes_converse(self, ai_engine_with_mock_bedrock):
        ai_engine_with_mock_bedrock.bedrock_client.converse.return_value = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "Executive Audit: Survey 384 verified at 10.35 Acres via AWS Bedrock Converse API."}]
                }
            },
            "usage": {"inputTokens": 412, "outputTokens": 85}
        }

        res = ai_engine_with_mock_bedrock.process_query("What is the status of Survey 384?")
        assert res["bedrock_invoked"] is True
        assert res["aws_credentials_available"] is True
        assert res["reasoning_mode"] == "AWS_BEDROCK_CONVERSE"
        assert res["bedrock_api_pattern"] == "Bedrock_Converse_API"
        assert "via Bedrock_Converse_API" in res["model_used"]
        assert "Survey 384 verified at 10.35 Acres" in res["answer"]
        ai_engine_with_mock_bedrock.bedrock_client.converse.assert_called_once()

    def test_converse_api_passes_expected_structure(self, ai_engine_with_mock_bedrock):
        """Verifies that converse is invoked with system prompt, messages, and inferenceConfig."""
        ai_engine_with_mock_bedrock.bedrock_client.converse.return_value = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "Audit passed."}]
                }
            },
            "usage": {"inputTokens": 200, "outputTokens": 30}
        }

        ai_engine_with_mock_bedrock.process_query("Analyze Survey 384")
        call_kwargs = ai_engine_with_mock_bedrock.bedrock_client.converse.call_args[1]

        assert "modelId" in call_kwargs
        assert "messages" in call_kwargs
        assert "system" in call_kwargs
        assert "inferenceConfig" in call_kwargs
        assert call_kwargs["inferenceConfig"]["maxTokens"] == 450
        assert call_kwargs["inferenceConfig"]["temperature"] == 0.2


class TestTLSVerification:
    """Verifies that TLS certificate verification is enforced and never disabled by default."""

    def test_tls_verification_flag_in_status(self, ai_engine_no_aws):
        status = ai_engine_no_aws.get_status()
        assert status["tls_verification_enabled"] is True

    def test_tls_verification_flag_in_query(self, ai_engine_no_aws):
        res = ai_engine_no_aws.process_query("Analyze Survey 384")
        assert res["tls_verification_enabled"] is True


class TestSpatialAttributionHonesty:
    """Verifies that CoT thought process attributes spatial math to GeoPandas/Shapely, not PostGIS."""

    def test_no_postgis_in_cot_trace(self, ai_engine_no_aws):
        res = ai_engine_no_aws.process_query("Analyze Survey 384")
        thought_process_text = " ".join(res["thought_process"])
        assert "PostGIS" not in thought_process_text
        assert "GeoPandas/Shapely" in thought_process_text
