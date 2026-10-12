import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from farmsync.orchestrator import FarmSyncOrchestrator

def main():
    print("Testing FarmSyncOrchestrator End-to-End...")
    orchestrator = FarmSyncOrchestrator()

    # Case 1: Standard Multimodal Request (Confident Path -> ACCEPT)
    print("\n--- Test Case 1: Confident Multimodal Workflow ---")
    query1 = "Using the supplied land document and field photograph for Keelathattaparai village, identify Survey Number 384, verify parcel and owner, predict crop and growth stage, and return verified recommendation."
    res1 = orchestrator.execute_request(query1)
    vobj1 = res1["verified_result_object"]
    print("Decision:", vobj1["trust_metrics"]["verification_status"])
    print("Trust Score (FTS):", vobj1["trust_metrics"]["task_trust_score_fts"])
    print("Extracted Owner:", vobj1["extracted_attributes"]["registered_owner"])
    print("GIS Area:", vobj1["extracted_attributes"]["gis_area_acres"], "acres")
    print("Crop:", vobj1["extracted_attributes"]["predicted_crop"], f"({vobj1['extracted_attributes']['growth_stage']})")
    print("Cost USD:", vobj1["routing_telemetry"]["total_estimated_cost_usd"])
    print("Baseline Savings:", res1["baseline_comparison"]["FARMSYNC"]["cost_savings_vs_premium_pct"], "%")
    assert vobj1["trust_metrics"]["verification_status"] == "VERIFIED_ACCEPT"

    # Case 2: Low-Confidence Perception -> Automatic Escalation to Teacher VLM
    print("\n--- Test Case 2: Low-Confidence Vision -> Teacher Escalation ---")
    res2 = orchestrator.execute_request(query1, force_escalate_vision=True)
    vobj2 = res2["verified_result_object"]
    print("Decision with Escalation:", vobj2["trust_metrics"]["verification_status"])
    print("Vision Model Used:", vobj2["routing_telemetry"]["steps"][3]["model_or_tool"])
    print("Escalation Rationale:", vobj2["routing_telemetry"]["steps"][3]["rationale"])
    assert "Claude-3.5-Sonnet-Teacher" in vobj2["routing_telemetry"]["steps"][3]["model_or_tool"]

    # Case 3: Injected Document-Registry Conflict -> Refuse-to-Invent ABSTAIN / Human Review
    print("\n--- Test Case 3: Injected Conflict -> ABSTAIN / Human Review ---")
    res3 = orchestrator.execute_request(query1, simulate_conflict=True)
    vobj3 = res3["verified_result_object"]
    print("Decision on Conflict:", vobj3["trust_metrics"]["verification_status"])
    print("Decision Message:", vobj3["trust_metrics"]["decision_message"])
    print("Trust Score (FTS):", vobj3["trust_metrics"]["task_trust_score_fts"])
    assert vobj3["trust_metrics"]["verification_status"] == "VERIFIED_ABSTAIN"

    print("\nALL END-TO-END ORCHESTRATION TESTS PASSED PERFECTLY!")

if __name__ == "__main__":
    main()
