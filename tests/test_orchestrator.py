import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from farmsync.orchestrator import FarmSyncOrchestrator

@pytest.fixture(scope="module")
def orchestrator():
    return FarmSyncOrchestrator()

def test_confident_multimodal_workflow(orchestrator):
    """Case 1: Standard Multimodal Request (Confident Path -> ACCEPT)"""
    query = "Using the supplied land document and field photograph for Keelathattaparai village, identify Survey Number 384, verify parcel and owner, predict crop and growth stage, and return verified recommendation."
    res = orchestrator.execute_request(query)
    vobj = res["verified_result_object"]

    assert vobj["trust_metrics"]["verification_status"] == "VERIFIED_ACCEPT"
    assert vobj["trust_metrics"]["task_trust_score_fts"] == 0.942
    assert vobj["extracted_attributes"]["predicted_crop"] == "Coconut"
    assert vobj["extracted_attributes"]["growth_stage"] == "full_growth"
    assert res["baseline_comparison"]["FARMSYNC"]["cost_savings_vs_premium_pct"] >= 80.0
    
    # Assert DAG execution state
    executed_dag = res["executed_dag"]
    assert executed_dag["workflow_type"] == "PARCEL_EVIDENCE_ADVISORY"
    assert len(executed_dag["subtasks"]) == 7
    for task in executed_dag["subtasks"]:
        assert task["status"] == "COMPLETED"
        assert task["has_result"] is True

def test_low_confidence_teacher_escalation(orchestrator):
    """Case 2: Low-Confidence Perception -> Automatic Escalation to Teacher VLM"""
    query = "Using the supplied land document and field photograph for Keelathattaparai village, identify Survey Number 384, verify parcel and owner, predict crop and growth stage, and return verified recommendation."
    res = orchestrator.execute_request(query, force_escalate_vision=True)
    vobj = res["verified_result_object"]

    assert vobj["trust_metrics"]["verification_status"] == "VERIFIED_ACCEPT"
    assert "Claude-3.5-Sonnet-Teacher" in vobj["routing_telemetry"]["steps"][3]["model_or_tool"]
    
    # Check Task 5 Multimodal Escalation Check
    task_5 = next(t for t in res["executed_dag"]["subtasks"] if t["id"] == "task_5")
    assert task_5["id"] == "task_5"
    assert task_5["status"] == "COMPLETED"
    assert "Claude-3.5-Sonnet-Teacher" in task_5["selected_route"]

def test_injected_conflict_abstention(orchestrator):
    """Case 3: Injected Document-Registry Conflict -> Refuse-to-Invent ABSTAIN / Human Review"""
    query = "Using the supplied land document and field photograph for Keelathattaparai village, identify Survey Number 384, verify parcel and owner, predict crop and growth stage, and return verified recommendation."
    res = orchestrator.execute_request(query, simulate_conflict=True)
    vobj = res["verified_result_object"]

    assert vobj["trust_metrics"]["verification_status"] == "VERIFIED_ABSTAIN"
    assert vobj["trust_metrics"]["task_trust_score_fts"] < 0.70


def main():
    print("Testing FarmSyncOrchestrator End-to-End...")
    orch = FarmSyncOrchestrator()
    print("\n--- Test Case 1: Confident Multimodal Workflow ---")
    test_confident_multimodal_workflow(orch)
    print("Case 1 passed!")
    print("\n--- Test Case 2: Low-Confidence Vision -> Teacher Escalation ---")
    test_low_confidence_teacher_escalation(orch)
    print("Case 2 passed!")
    print("\n--- Test Case 3: Injected Conflict -> ABSTAIN / Human Review ---")
    test_injected_conflict_abstention(orch)
    print("Case 3 passed!")
    print("\nALL END-TO-END ORCHESTRATION TESTS PASSED PERFECTLY!")


if __name__ == "__main__":
    main()
