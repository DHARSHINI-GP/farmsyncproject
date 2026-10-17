import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from farmsync.router.compiler import TaskGraphCompiler, TaskGraph, TaskNode
from farmsync.router.router import CapabilityRegistry, VerifiedUtilityRouter


def test_verified_utility_formula_exact():
    """
    Validates that compute_utility calculates:
    RouteScore = alpha*Quality - beta*Cost - gamma*Latency - delta*Risk + eta*VerifGain
    with default weights: alpha=1.0, beta=50.0, gamma=0.25, delta=1.2, eta=0.6.
    """
    router = VerifiedUtilityRouter()
    
    # Test candidate: Quality=0.95, Cost=$0.0004, Latency=80ms (0.08s), Risk=0.05, VerifGain=0.20
    test_cand = {
        "route": "Test_Candidate",
        "type": "TEST",
        "cost_per_call": 0.0004,
        "typical_latency_ms": 80,
        "quality_score": 0.95,
        "failure_risk": 0.05,
        "verification_gain": 0.20
    }
    
    utility = router.compute_utility(test_cand, "VISION_STUDENT")
    
    # Expected:
    # Quality: 1.0 * 0.95 = 0.95
    # Cost: 50.0 * 0.0004 = 0.02
    # Latency: 0.25 * 0.08 = 0.02
    # Risk: 1.2 * 0.05 = 0.06
    # Gain: 0.6 * 0.20 = 0.12
    # Score = 0.95 - 0.02 - 0.02 - 0.06 + 0.12 = 0.97
    assert utility["route_score"] == 0.97
    assert utility["cost_penalty"] == 0.02
    assert utility["latency_penalty"] == 0.02
    assert utility["risk_penalty"] == 0.06
    assert utility["verif_gain_term"] == 0.12


def test_deterministic_spatial_wins_over_llm():
    """
    Validates that GeoPandas/Shapely deterministic engine mathematically defeats LLM spatial reasoning
    due to zero cost, minimal latency, and zero hallucination risk.
    """
    router = VerifiedUtilityRouter()
    decision = router.select_optimal_route("GEOSPATIAL_GIS")
    
    assert decision["selected_route"] == "GeoPandas_Shapely_Engine"
    assert decision["route_type"] == "DETERMINISTIC_TOOL"
    assert decision["route_score"] > 1.2  # High utility
    
    # Check that LLM spatial alternative was evaluated and had lower utility
    alternatives = decision["alternatives_evaluated"]
    llm_alt = next(a for a in alternatives if "LLM" in a["route"])
    assert decision["route_score"] > llm_alt["score"]


def test_dynamic_confidence_escalation():
    """
    Validates that router escalates based on measured confidence:
    - High confidence (0.98) -> Selects Accept_Student_Perception (saves $0.0045)
    - Low confidence (0.45) -> Mathematically selects Bedrock-Ministral-8B-Teacher by argmax
    """
    router = VerifiedUtilityRouter()

    # Confident scenario (C = 0.98)
    route_confident = router.select_optimal_route("VERIFICATION_ESCALATION", measured_confidence=0.98)
    assert route_confident["selected_route"] == "Accept_Student_Perception"
    assert route_confident["estimated_cost_usd"] == 0.0

    # Low-confidence / Ambiguous scenario (C = 0.45)
    route_uncertain = router.select_optimal_route("VERIFICATION_ESCALATION", measured_confidence=0.45)
    assert route_uncertain["selected_route"] == "Bedrock-Ministral-8B-Teacher"
    assert route_uncertain["estimated_cost_usd"] == 0.0045
    assert "Escalated to proprietary VLM" in route_uncertain["routing_rationale"]


def test_task_graph_topological_sort_and_dependencies():
    """
    Validates that TaskGraph builds an acyclic DAG and executes nodes in valid topological order.
    """
    compiler = TaskGraphCompiler()
    graph = compiler.compile("Please check survey 384 in Keelathattaparai village")
    
    ordered = graph.topological_sort()
    ordered_ids = [n.id for n in ordered]
    
    # Task 1 (OCR) and Task 4 (Vision Student) have no dependencies
    assert ordered_ids.index("task_1") < ordered_ids.index("task_2")
    assert ordered_ids.index("task_2") < ordered_ids.index("task_3")
    assert ordered_ids.index("task_4") < ordered_ids.index("task_5")
    assert ordered_ids.index("task_5") < ordered_ids.index("task_6")
    assert ordered_ids.index("task_3") < ordered_ids.index("task_7")
    assert ordered_ids.index("task_6") < ordered_ids.index("task_7")

    # Dependency checking
    completed = set()
    assert graph.are_deps_satisfied("task_1", completed) is True
    assert graph.are_deps_satisfied("task_2", completed) is False
    
    completed.add("task_1")
    assert graph.are_deps_satisfied("task_2", completed) is True


def test_task_graph_runtime_state_updates():
    """
    Validates that task nodes accurately transition from PENDING -> RUNNING -> COMPLETED
    and retain route decisions and execution outputs.
    """
    node = TaskNode("task_test", "Test Task", "DOCUMENT_OCR")
    assert node.status == "PENDING"
    assert node.cost_usd == 0.0

    node.mark_running()
    assert node.status == "RUNNING"

    route_mock = {
        "selected_route": "pdfplumber_Table_OCR_Extractor",
        "route_type": "SPECIALIZED_MODEL",
        "route_score": 1.25,
        "routing_rationale": "High precision table parser"
    }
    result_mock = {"survey_no": "384", "owner": "Ramesh G"}
    node.mark_completed(result=result_mock, cost_usd=0.0002, latency_ms=115, route_decision=route_mock)

    assert node.status == "COMPLETED"
    assert node.selected_route == "pdfplumber_Table_OCR_Extractor"
    assert node.route_score == 1.25
    assert node.cost_usd == 0.0002
    assert node.latency_ms == 115
    assert node.result == result_mock


def test_cycle_detection():
    """
    Validates that TaskGraph detects cyclic graphs and raises ValueError.
    """
    graph = TaskGraph("CYCLIC_TEST", "Test cyclic DAG")
    node_a = TaskNode("A", "Node A", "TEST", deps=["B"])
    node_b = TaskNode("B", "Node B", "TEST", deps=["A"])
    graph.add_node(node_a)
    graph.add_node(node_b)

    with pytest.raises(ValueError, match="Cycle detected"):
        graph.topological_sort()


if __name__ == "__main__":
    print("Running Router and DAG tests manually...")
    test_verified_utility_formula_exact()
    test_deterministic_spatial_wins_over_llm()
    test_dynamic_confidence_escalation()
    test_task_graph_topological_sort_and_dependencies()
    test_task_graph_runtime_state_updates()
    test_cycle_detection()
    print("ALL ROUTER & DAG TESTS PASSED SUCCESSFULLY!")
