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
        assert "Survey 384 verified at 10.35 Acres" not in res["answer"]
        assert res["answer_source"] == "VERIFIED_TOOL_TEMPLATE"
        assert "No live government ownership" in res["answer"]
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
        assert call_kwargs["inferenceConfig"]["maxTokens"] == 40
        assert call_kwargs["inferenceConfig"]["temperature"] == 0

    @pytest.mark.parametrize("model_text", [
        "The government portal confirms Ramesh owns this land and has no litigation.",
        '{"focus":"crop","answer":"Government ownership confirmed"}',
        '{"focus":"Government ownership confirmed"}',
        '{"focus":["crop"]}',
    ])
    def test_generated_claims_cannot_enter_verified_report(self, ai_engine_with_mock_bedrock, model_text):
        eng = ai_engine_with_mock_bedrock
        eng.bedrock_client.converse.return_value = {"output": {"message": {"content": [{"text": model_text}]}}}
        result = eng.process_query("Confirm ownership of Survey 384")
        assert "Government ownership confirmed" not in result["answer"]
        assert "government portal confirms" not in result["answer"]
        assert result["report_focus"] == "general"
        assert result["answer_source"] == "VERIFIED_TOOL_TEMPLATE"

    def test_valid_model_focus_can_reorder_only_grounded_sections(self, ai_engine_with_mock_bedrock):
        eng = ai_engine_with_mock_bedrock
        eng.bedrock_client.converse.return_value = {"output": {"message": {"content": [{"text": '{"focus":"crop"}'}]}}}
        result = eng.process_query("Inspect crop in Survey 384")
        assert result["report_focus"] == "crop"
        assert result["answer"].startswith("### Field Intelligence")


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


def test_missing_document_extent_does_not_become_a_discrepancy(ai_engine_no_aws,monkeypatch):
    monkeypatch.setattr(ai_engine_no_aws.orchestrator.docs,'extract_document_claims',lambda **_: {
        'found':True,'document_source':'partial.pdf','survey_no':'384',
        'extracted_owner':'Actual Source Name','claimed_extent_acres':None,
        'status':'PARTIAL_SOURCE_EVIDENCE','page_number':2})
    result=ai_engine_no_aws.process_query('Analyze Survey 384')
    assert result['document_verification']['verification_status']=='UNRESOLVED'
    assert result['document_verification']['page_count'] is None
    assert 'Document Comparison Unresolved' in result['answer']


def test_custom_buffer_answer_reports_the_executed_spatial_rule(ai_engine_no_aws):
    result=ai_engine_no_aws.process_query('Check a 100 m waterbody buffer for Survey 384')
    assert result['spatial_verification']['waterbody_buffer_threshold_meters']==100
    assert result['answer'].startswith('### Spatial Audit:')
    assert '**100 m**' in result['answer']
    assert str(result['spatial_verification']['distance_to_waterbody_meters']) in result['answer']
    assert 'does not establish legal clearance' in result['answer']
