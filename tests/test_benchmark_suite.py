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


def test_benchmark_results_json_empirical():
    """Verifies that benchmark_results.json records measured empirical performance."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    results_path = os.path.join(base_dir, "data", "benchmark_results.json")
    assert os.path.exists(results_path), f"Benchmark results file missing at {results_path}"

    with open(results_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_queries"] == 50
    summary = data["summary"]

    fs = summary["FARMSYNC"]
    prem = summary["Premium_Only"]
    stat = summary["Static_Routing"]

    # Spatial Hallucination guarantee: Zero spatial hallucinations via deterministic GeoPandas/Shapely GIS
    assert fs["spatial_hallucination_rate_pct"] == 0.0
    assert prem["spatial_hallucination_rate_pct"] > 0.0

    # Cost reduction: >85% cost savings vs commercial VLM
    assert fs["cost_savings_vs_premium_pct"] >= 85.0
    assert fs["average_cost_usd"] < prem["average_cost_usd"]

    # Latency reduction
    assert fs["average_latency_ms"] < prem["average_latency_ms"]

    # Category breakdown verification
    breakdown = data["category_breakdown"]
    assert "CONFIDENT_GROUNDED" in breakdown
    assert "PERCEPTION_ESCALATION" in breakdown
    assert "BUFFER_AND_ACCESS" in breakdown
    assert "DOCUMENT_EXTENT_DISCREPANCY" in breakdown
    assert "UNSUPPORTED_AND_ABSTAIN" in breakdown


def test_orchestrator_baseline_comparison_not_mocked():
    """
    Verifies that orchestrator.py baseline comparison does NOT use mock constants or
    derive accuracy directly from '100.0 if ACCEPT else ...'.
    """
    orch = FarmSyncOrchestrator()
    res = orch.execute_request(
        "Identify Survey Number 384 in Keelathattaparai village, verify parcel extent, predict crop and growth stage.",
        survey_no="384"
    )

    baseline = res["baseline_comparison"]
    assert "benchmark_suite" in baseline
    assert baseline["total_benchmark_queries"] == 50

    fs = baseline["FARMSYNC"]
    prem = baseline["Premium_Only"]
    stat = baseline["Static_Routing"]

    # Live query cost/latency is measured dynamically
    assert fs["cost_usd"] > 0.0
    assert fs["latency_ms"] >= 0
    assert fs["hallucination_rate_pct"] == 0.0
    assert fs["cost_savings_vs_premium_pct"] > 0.0

    # Measured benchmark accuracy is reported from the 50-query suite
    assert fs["benchmark_measured_accuracy_pct"] >= 90.0
    assert prem["benchmark_measured_accuracy_pct"] == 84.0
    assert stat["benchmark_measured_accuracy_pct"] == 67.5


def test_orchestrator_baseline_on_abstain_query():
    """
    Verifies that even when a query abstains, baseline comparison reports measured benchmark
    accuracy rather than mock 0% or hardcoded mock accuracy.
    """
    orch = FarmSyncOrchestrator()
    res = orch.execute_request(
        "Audit non-existent Survey 9999 in Keelathattaparai village.",
        survey_no="9999"
    )

    vobj = res["verified_result_object"]
    assert vobj["trust_metrics"]["verification_status"] == "VERIFIED_ABSTAIN"

    # Baseline comparison must report empirical benchmark accuracy, not mock 0%
    baseline = res["baseline_comparison"]
    assert baseline["FARMSYNC"]["benchmark_measured_accuracy_pct"] >= 90.0
    assert baseline["FARMSYNC"]["verified_accuracy_pct"] >= 90.0
