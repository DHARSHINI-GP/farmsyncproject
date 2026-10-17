import os
import json
import pytest

from farmsync.benchmark.dataset import get_benchmark_queries, save_benchmark_queries_json
from farmsync.benchmark.evaluator import BenchmarkEvaluator
from farmsync.orchestrator import FarmSyncOrchestrator


def test_benchmark_dataset_structure():
    """Verifies that the benchmark dataset contains exactly 50 queries across all 5 categories."""
    queries = get_benchmark_queries()
    assert len(queries) == 50, f"Expected 50 queries, got {len(queries)}"

    categories = {q["category"] for q in queries}
    expected_categories = {
        "CONFIDENT_GROUNDED",
        "PERCEPTION_ESCALATION",
        "BUFFER_AND_ACCESS",
        "DOCUMENT_EXTENT_DISCREPANCY",
        "UNSUPPORTED_AND_ABSTAIN"
    }
    assert categories == expected_categories

    counts = {}
    for q in queries:
        counts[q["category"]] = counts.get(q["category"], 0) + 1

    assert counts["CONFIDENT_GROUNDED"] == 22
    assert counts["PERCEPTION_ESCALATION"] == 8
    assert counts["BUFFER_AND_ACCESS"] == 6
    assert counts["DOCUMENT_EXTENT_DISCREPANCY"] == 8
    assert counts["UNSUPPORTED_AND_ABSTAIN"] == 6


def test_historical_results_are_not_current_accuracy_evidence():
    from pathlib import Path
    data=json.loads(Path("data/benchmark_results.json").read_text(encoding="utf-8"))
    assert data["status"] == "HISTORICAL_INVALID_AFTER_SOURCE_EVIDENCE_FIXES"
    assert data["current_configuration_validated"] is False


def test_current_metrics_do_not_fabricate_comparisons():
    orch=FarmSyncOrchestrator()
    result=orch.execute_request("Check waterbody buffer for Survey 384")
    baseline=result["baseline_comparison"]
    assert baseline["current_configuration_validated"] is False
    assert baseline["FARMSYNC"]["latency_ms"] >= 0
    assert baseline["FARMSYNC"]["verified_accuracy_pct"] is None
    assert baseline["FARMSYNC"]["hallucination_rate_pct"] is None
    assert baseline["FARMSYNC"]["cost_savings_vs_premium_pct"] is None
    assert baseline["Premium_Only"]["evaluation_type"] == "NOT_EXECUTED"


def test_competitor_baseline_runners_executed_query_by_query():
    """
    Verifies that StaticPipelineRunner and PremiumVLMRunner execute genuinely query-by-query
    and exhibit authentic domain strengths and failure modes.
    """
    from farmsync.benchmark.baselines import StaticPipelineRunner, PremiumVLMRunner, score_ground_truth

    static_runner = StaticPipelineRunner()
    prem_runner = PremiumVLMRunner()

    # 1. Perception Escalation Query: Static fails (never escalates), Premium succeeds (teacher VLM)
    q_esc = {
        "id": "TEST-ESC",
        "category": "PERCEPTION_ESCALATION",
        "query": "Identify crop under low light on Survey 384",
        "survey_no": "384",
        "expected_crop": "Coconut",
        "gis_acres": 10.349,
        "expected_decision": "ACCEPT",
        "force_escalate": True
    }
    static_res = static_runner.execute_query(q_esc)
    assert static_res["escalated_to_teacher"] is False
    stat_acc, _ = score_ground_truth(q_esc, static_res)
    assert stat_acc is False, "Static pipeline must fail perception escalation because it lacks teacher routing"

    prem_res = prem_runner.execute_query(q_esc)
    assert prem_res["escalated_to_teacher"] is True
    prem_acc, _ = score_ground_truth(q_esc, prem_res)
    assert prem_acc is True, "Premium VLM succeeds on multimodal perception escalation"

    # 2. Buffer & Access Query: Both competitors fail deterministic buffer verification
    q_buf = {
        "id": "TEST-BUF",
        "category": "BUFFER_AND_ACCESS",
        "query": "Verify 50m waterbody buffer on Survey 384",
        "survey_no": "384",
        "expected_crop": "Coconut",
        "gis_acres": 10.349,
        "expected_decision": "ACCEPT"
    }
    static_buf_res = static_runner.execute_query(q_buf)
    stat_buf_acc, stat_halluc = score_ground_truth(q_buf, static_buf_res)
    assert stat_buf_acc is False
    assert stat_halluc == 1.0

    prem_buf_res = prem_runner.execute_query(q_buf)
    prem_buf_acc, prem_halluc = score_ground_truth(q_buf, prem_buf_res)
    assert prem_buf_acc is False
    assert prem_halluc == 1.0, "Commercial VLM hallucinates spatial buffer calculations"


def test_evaluator_strict_buffer_and_telemetry_checks():
    """
    Verifies that score_ground_truth enforces strict multi-point verification:
    - BUFFER_AND_ACCESS queries MUST verify positive distance, compliance booleans, and verified flag.
    - PERCEPTION_ESCALATION queries MUST prove actual teacher execution (no fake fallback).
    """
    from farmsync.benchmark.baselines import score_ground_truth

    # Test 1: Buffer check with missing distance fails
    q_buf = {
        "id": "TEST-BUF-STRICT",
        "category": "BUFFER_AND_ACCESS",
        "gis_acres": 10.349,
        "expected_decision": "ACCEPT"
    }
    mock_incomplete_buffer = {
        "decision": "ACCEPT",
        "gis_area_acres": 10.349,
        "deterministic_spatial_checks": {
            "distance_to_waterbody_meters": None,  # Missing!
            "waterbody_buffer_50m_compliant": True,
            "waterbody_buffer_conflict": False,
            "distance_to_road_meters": 50.0,
            "road_accessible": True,
            "deterministic_spatial_verified": True
        }
    }
    acc, halluc = score_ground_truth(q_buf, mock_incomplete_buffer)
    assert acc is False
    assert halluc == 1.0

    # Test 2: Buffer check with waterbody conflict fails
    mock_conflict_buffer = {
        "decision": "ACCEPT",
        "gis_area_acres": 10.349,
        "deterministic_spatial_checks": {
            "distance_to_waterbody_meters": 25.0,
            "waterbody_buffer_50m_compliant": False,  # Non-compliant!
            "waterbody_buffer_conflict": True,
            "distance_to_road_meters": 50.0,
            "road_accessible": True,
            "deterministic_spatial_verified": True
        }
    }
    acc, halluc = score_ground_truth(q_buf, mock_conflict_buffer)
    assert acc is False

    # Test 3: Perception escalation without actual teacher execution fails
    q_esc = {
        "id": "TEST-ESC-STRICT",
        "category": "PERCEPTION_ESCALATION",
        "expected_crop": "Coconut",
        "expected_decision": "ACCEPT"
    }
    mock_no_teacher = {
        "decision": "ACCEPT",
        "predicted_crop": "Coconut",  # Correct crop, but...
        "escalated_to_teacher": False  # Telemetry shows NO teacher escalation!
    }
    acc, _ = score_ground_truth(q_esc, mock_no_teacher)
    assert acc is False, "Perception escalation must fail if telemetry does not prove teacher execution"

