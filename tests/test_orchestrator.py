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
    assert vobj["trust_metrics"]["task_trust_score_fts"] >= 0.85
    assert vobj["trust_metrics"]["signal_breakdown"]["evidence_coverage"] == 0.67
    assert vobj["trust_metrics"]["signal_breakdown"]["conflict_penalty"] == 0.0
    assert vobj["extracted_attributes"]["ownership_verified"] is False
    assert vobj["extracted_attributes"]["ownership_status"] == "DEMO_MATCH_NOT_OFFICIAL_VERIFICATION"
    assert vobj["extracted_attributes"]["demo_record_matched"] is True
    assert vobj["extracted_attributes"]["is_authoritative_government_record"] is False
    assert vobj["extracted_attributes"]["parcel_geometry_verified"] is True
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

def test_agri_logistics_integration(orchestrator):
    """Case 4: Agri-Logistics & Routing Integration in Verified Result Object & DAG"""
    query = "Using the supplied land document and field photograph for Keelathattaparai village, identify Survey Number 384, verify parcel and owner, predict crop and growth stage, and return verified recommendation."
    res = orchestrator.execute_request(query)
    vobj = res["verified_result_object"]

    # Agri-logistics must be included in the verified result
    assert "agri_logistics" in vobj
    logistics = vobj["agri_logistics"]
    assert logistics is not None
    assert logistics["survey_no"] == "384"
    assert logistics["distance_km"] > 0
    assert "duration_minutes" in logistics
    assert "LOCAL_HAVERSINE_ESTIMATE" in logistics["source"] or "Amazon Location" in logistics["source"]

    # Source evidence must record logistics routing
    logistics_evidence = next((s for s in vobj["source_evidence"] if s["source_type"] == "AGRI_LOGISTICS_ROUTING"), None)
    assert logistics_evidence is not None
    assert logistics_evidence["distance_km"] == logistics["distance_km"]

    # Evidence graph DAG must contain a LOGISTICS_ROUTE node
    logistics_node = next((n for n in vobj["evidence_graph_dag"]["nodes"] if n["type"] == "LOGISTICS_ROUTE"), None)
    assert logistics_node is not None
    assert "Transit:" in logistics_node["label"]


def test_environmental_buffer_audit_workflow(orchestrator):
    """
    Case 5: Environmental Buffer & Spatial Audit Workflow
    Validates that:
    1. Workflow is compiled to ENVIRONMENTAL_BUFFER_AUDIT DAG
    2. Does NOT fabricate has_field_photo=True or has_land_doc=True
    3. Keeps parcel_geometry_verified separate from ownership_verified
    4. ownership_verified is strictly False (no land doc / registry matched)
    5. parcel_geometry_verified is True for valid Survey 384
    6. Waterbody buffer compliance and deterministic spatial checks pass
    7. FTS >= 0.85 and decision is VERIFIED_ACCEPT
    """
    query = "Check 50m waterbody buffer compliance and access road distance for Survey 384 in Keelathattaparai village."
    res = orchestrator.execute_request(query, survey_no="384")
    vobj = res["verified_result_object"]

    # Workflow DAG verification
    assert res["executed_dag"]["workflow_type"] == "ENVIRONMENTAL_BUFFER_AUDIT"
    assert len(res["executed_dag"]["subtasks"]) == 4

    # Separation of geometry vs ownership verification
    attrs = vobj["extracted_attributes"]
    assert attrs["ownership_verified"] is False
    assert attrs["registered_owner"] is None
    assert attrs["parcel_geometry_verified"] is True
    assert attrs["gis_area_acres"] == 10.349
    assert attrs["predicted_crop"] is None
    assert attrs["document_found"] is False

    # Deterministic spatial checks
    spatial = vobj["deterministic_spatial_checks"]
    assert spatial["geometry_valid"] is True
    assert spatial["waterbody_buffer_50m_compliant"] is True
    assert spatial["waterbody_buffer_conflict"] is False
    assert spatial["deterministic_spatial_verified"] is True

    # Trust Engine decision
    assert vobj["trust_metrics"]["verification_status"] == "VERIFIED_ACCEPT"
    assert vobj["trust_metrics"]["task_trust_score_fts"] >= 0.85


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
    print("\n--- Test Case 4: Agri-Logistics Integration ---")
    test_agri_logistics_integration(orch)
    print("Case 4 passed!")
    print("\n--- Test Case 5: Environmental Buffer Audit Workflow ---")
    test_environmental_buffer_audit_workflow(orch)
    print("Case 5 passed!")
    print("\nALL END-TO-END ORCHESTRATION TESTS PASSED PERFECTLY!")


if __name__ == "__main__":
    main()
