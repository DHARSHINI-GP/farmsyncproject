"""
FARMSYNC 50-Query Benchmark Dataset Definition.
Curates 50 authentic, reproducible benchmark queries spanning 5 representative categories
to measure head-to-head performance across FARMSYNC, Premium VLM, and Static baselines.
"""

import os
import json
from typing import List, Dict, Any

def get_benchmark_queries() -> List[Dict[str, Any]]:
    """Returns the standardized 50-query benchmark dataset with ground truth annotations."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    json_path = os.path.join(base_dir, "data", "benchmark_50_queries.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "queries" in data and len(data["queries"]) == 50:
                    return data["queries"]
        except Exception:
            pass

    queries = [
        # ── CATEGORY 1: CONFIDENT GROUNDED PARCELS (22 Queries) ───────────────────
        {
            "id": "BENCH-01",
            "category": "CONFIDENT_GROUNDED",
            "query": "Identify Survey Number 384 in Keelathattaparai village, verify parcel extent, predict crop and growth stage, and return agronomy advisory.",
            "survey_no": "384",
            "village": "Keelathattaparai",
            "expected_crop": "Coconut",
            "expected_stage": "full_growth",
            "gis_acres": 10.349,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-02",
            "category": "CONFIDENT_GROUNDED",
            "query": "Verify cadastral parcel S.No. 381 in Keelathattaparai village, extract registered owner, and provide crop recommendation.",
            "survey_no": "381",
            "village": "Keelathattaparai",
            "expected_crop": "Rice (Paddy)",
            "expected_stage": "full_growth",
            "gis_acres": 4.210,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-03",
            "category": "CONFIDENT_GROUNDED",
            "query": "Audit Survey Number 174 in Keelathattaparai village, verify land records and predict standing crop.",
            "survey_no": "174",
            "village": "Keelathattaparai",
            "expected_crop": "Maize",
            "expected_stage": "vegetation",
            "gis_acres": 6.240,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-04",
            "category": "CONFIDENT_GROUNDED",
            "query": "Check parcel boundary and crop stage for Survey 387 in Keelathattaparai village.",
            "survey_no": "387",
            "village": "Keelathattaparai",
            "expected_crop": "Sugarcane",
            "expected_stage": "full_growth",
            "gis_acres": 8.500,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-05",
            "category": "CONFIDENT_GROUNDED",
            "query": "Verify extent and crop health for Survey Number 388 in Keelathattaparai.",
            "survey_no": "388",
            "village": "Keelathattaparai",
            "expected_crop": "Coconut",
            "expected_stage": "full_growth",
            "gis_acres": 9.400,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-06",
            "category": "CONFIDENT_GROUNDED",
            "query": "Audit agricultural parcel Survey 385 in Keelathattaparai village with field photograph.",
            "survey_no": "385",
            "village": "Keelathattaparai",
            "expected_crop": "Cotton",
            "expected_stage": "vegetation",
            "gis_acres": 5.600,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-07",
            "category": "CONFIDENT_GROUNDED",
            "query": "Verify land title and predict crop for Survey 386 in Keelathattaparai village.",
            "survey_no": "386",
            "village": "Keelathattaparai",
            "expected_crop": "Groundnut",
            "expected_stage": "vegetation",
            "gis_acres": 6.750,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-08",
            "category": "CONFIDENT_GROUNDED",
            "query": "Run verification audit on Survey Number 81 in Keelathattaparai village.",
            "survey_no": "81",
            "village": "Keelathattaparai",
            "expected_crop": "Sorghum",
            "expected_stage": "vegetation",
            "gis_acres": 2.496,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-09",
            "category": "CONFIDENT_GROUNDED",
            "query": "Audit plot at Survey 83 in Keelathattaparai, verify ownership and agronomic recommendations.",
            "survey_no": "83",
            "village": "Keelathattaparai",
            "expected_crop": "Banana",
            "expected_stage": "full_growth",
            "gis_acres": 1.112,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-10",
            "category": "CONFIDENT_GROUNDED",
            "query": "Verify cadastral parcel Survey 1 in Keelathattaparai village with GIS acreage and crop advisory.",
            "survey_no": "1",
            "village": "Keelathattaparai",
            "expected_crop": "Coconut",
            "expected_stage": "full_growth",
            "gis_acres": 17.495,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-11",
            "category": "CONFIDENT_GROUNDED",
            "query": "Check land record and crop classification for Survey 10 in Keelathattaparai village.",
            "survey_no": "10",
            "village": "Keelathattaparai",
            "expected_crop": "Coconut",
            "expected_stage": "full_growth",
            "gis_acres": 25.040,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-12",
            "category": "CONFIDENT_GROUNDED",
            "query": "Perform agricultural audit on Survey Number 11 in Keelathattaparai village.",
            "survey_no": "11",
            "village": "Keelathattaparai",
            "expected_crop": "Rice (Paddy)",
            "expected_stage": "full_growth",
            "gis_acres": 11.762,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-13",
            "category": "CONFIDENT_GROUNDED",
            "query": "Audit parcel boundaries and crop stage for Survey 105 in Keelathattaparai village.",
            "survey_no": "105",
            "village": "Keelathattaparai",
            "expected_crop": "Rice (Paddy)",
            "expected_stage": "vegetation",
            "gis_acres": 8.325,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-14",
            "category": "CONFIDENT_GROUNDED",
            "query": "Verify crop identification and land parcel extent for Survey 106 in Keelathattaparai.",
            "survey_no": "106",
            "village": "Keelathattaparai",
            "expected_crop": "Coconut",
            "expected_stage": "full_growth",
            "gis_acres": 12.245,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-15",
            "category": "CONFIDENT_GROUNDED",
            "query": "Check agricultural attributes and advisory for Survey 107 in Keelathattaparai village.",
            "survey_no": "107",
            "village": "Keelathattaparai",
            "expected_crop": "Banana",
            "expected_stage": "full_growth",
            "gis_acres": 10.594,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-16",
            "category": "CONFIDENT_GROUNDED",
            "query": "Audit parcel extent and standing crop for Survey 108 in Keelathattaparai village.",
            "survey_no": "108",
            "village": "Keelathattaparai",
            "expected_crop": "Coconut",
            "expected_stage": "full_growth",
            "gis_acres": 9.845,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-17",
            "category": "CONFIDENT_GROUNDED",
            "query": "Verify legal title and standing crop for Survey 109 in Keelathattaparai village.",
            "survey_no": "109",
            "village": "Keelathattaparai",
            "expected_crop": "Coconut",
            "expected_stage": "full_growth",
            "gis_acres": 8.473,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-18",
            "category": "CONFIDENT_GROUNDED",
            "query": "Perform land audit on Survey 110 in Keelathattaparai village.",
            "survey_no": "110",
            "village": "Keelathattaparai",
            "expected_crop": "Coconut",
            "expected_stage": "full_growth",
            "gis_acres": 12.237,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-19",
            "category": "CONFIDENT_GROUNDED",
            "query": "Audit Survey Number 111 in Keelathattaparai village, verify parcel area and crop recommendation.",
            "survey_no": "111",
            "village": "Keelathattaparai",
            "expected_crop": "Coconut",
            "expected_stage": "full_growth",
            "gis_acres": 6.590,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-20",
            "category": "CONFIDENT_GROUNDED",
            "query": "Audit cadastral parcel Survey 112 in Keelathattaparai village.",
            "survey_no": "112",
            "village": "Keelathattaparai",
            "expected_crop": "Rice (Paddy)",
            "expected_stage": "vegetation",
            "gis_acres": 14.150,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-21",
            "category": "CONFIDENT_GROUNDED",
            "query": "Verify Survey Number 113 in Keelathattaparai village and provide agronomy advisory.",
            "survey_no": "113",
            "village": "Keelathattaparai",
            "expected_crop": "Coconut",
            "expected_stage": "full_growth",
            "gis_acres": 9.180,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-22",
            "category": "CONFIDENT_GROUNDED",
            "query": "Audit parcel boundaries and crop stage for Survey 114 in Keelathattaparai village.",
            "survey_no": "114",
            "village": "Keelathattaparai",
            "expected_crop": "Banana",
            "expected_stage": "full_growth",
            "gis_acres": 7.820,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },

        # ── CATEGORY 2: PERCEPTION ESCALATION (8 Queries) ─────────────────────────
        {
            "id": "BENCH-23",
            "category": "PERCEPTION_ESCALATION",
            "query": "Perform enhanced visual verification with teacher escalation for Survey 384 in Keelathattaparai.",
            "survey_no": "384",
            "village": "Keelathattaparai",
            "expected_crop": "Coconut",
            "expected_stage": "full_growth",
            "gis_acres": 10.349,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": True,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-24",
            "category": "PERCEPTION_ESCALATION",
            "query": "Run deep multimodal inspection with foundation teacher for Survey 381 in Keelathattaparai.",
            "survey_no": "381",
            "village": "Keelathattaparai",
            "expected_crop": "Rice (Paddy)",
            "expected_stage": "full_growth",
            "gis_acres": 4.210,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": True,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-25",
            "category": "PERCEPTION_ESCALATION",
            "query": "Execute high-precision crop classification for Survey 387 with perception escalation.",
            "survey_no": "387",
            "village": "Keelathattaparai",
            "expected_crop": "Sugarcane",
            "expected_stage": "full_growth",
            "gis_acres": 8.500,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": True,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-26",
            "category": "PERCEPTION_ESCALATION",
            "query": "Audit dense canopy field for Survey 174 with teacher escalation.",
            "survey_no": "174",
            "village": "Keelathattaparai",
            "expected_crop": "Maize",
            "expected_stage": "vegetation",
            "gis_acres": 6.240,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": True,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-27",
            "category": "PERCEPTION_ESCALATION",
            "query": "High-confidence perception check on Survey 388 with teacher ensemble verification.",
            "survey_no": "388",
            "village": "Keelathattaparai",
            "expected_crop": "Coconut",
            "expected_stage": "full_growth",
            "gis_acres": 9.400,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": True,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-28",
            "category": "PERCEPTION_ESCALATION",
            "query": "Verify Survey 385 cotton stage with multi-scale test-time augmentation escalation.",
            "survey_no": "385",
            "village": "Keelathattaparai",
            "expected_crop": "Cotton",
            "expected_stage": "vegetation",
            "gis_acres": 5.600,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": True,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-29",
            "category": "PERCEPTION_ESCALATION",
            "query": "Deep perception verification of Survey 386 groundnut field with teacher escalation.",
            "survey_no": "386",
            "village": "Keelathattaparai",
            "expected_crop": "Groundnut",
            "expected_stage": "vegetation",
            "gis_acres": 6.750,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": True,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-30",
            "category": "PERCEPTION_ESCALATION",
            "query": "Escalated visual inspection on Survey 83 banana plantation in Keelathattaparai.",
            "survey_no": "83",
            "village": "Keelathattaparai",
            "expected_crop": "Banana",
            "expected_stage": "full_growth",
            "gis_acres": 1.112,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": True,
            "simulate_conflict": False
        },

        # ── CATEGORY 3: BUFFER & ACCESS CHECKS (6 Queries) ────────────────────────
        {
            "id": "BENCH-31",
            "category": "BUFFER_AND_ACCESS",
            "query": "Check 50m waterbody buffer compliance and access road distance for Survey 384.",
            "survey_no": "384",
            "village": "Keelathattaparai",
            "expected_crop": "Coconut",
            "expected_stage": "full_growth",
            "gis_acres": 10.349,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-32",
            "category": "BUFFER_AND_ACCESS",
            "query": "Evaluate legal environmental setback and logistics route for Survey 381 in Keelathattaparai.",
            "survey_no": "381",
            "village": "Keelathattaparai",
            "expected_crop": "Rice (Paddy)",
            "expected_stage": "full_growth",
            "gis_acres": 4.210,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-33",
            "category": "BUFFER_AND_ACCESS",
            "query": "Verify road network access and substation proximity for Survey 174 in Keelathattaparai.",
            "survey_no": "174",
            "village": "Keelathattaparai",
            "expected_crop": "Maize",
            "expected_stage": "vegetation",
            "gis_acres": 6.240,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-34",
            "category": "BUFFER_AND_ACCESS",
            "query": "Check waterbody buffer threshold compliance and depot route for Survey 387.",
            "survey_no": "387",
            "village": "Keelathattaparai",
            "expected_crop": "Sugarcane",
            "expected_stage": "full_growth",
            "gis_acres": 8.500,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-35",
            "category": "BUFFER_AND_ACCESS",
            "query": "Verify spatial constraints and environmental buffers for Survey 388.",
            "survey_no": "388",
            "village": "Keelathattaparai",
            "expected_crop": "Coconut",
            "expected_stage": "full_growth",
            "gis_acres": 9.400,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-36",
            "category": "BUFFER_AND_ACCESS",
            "query": "Audit environmental compliance and road connectivity for Survey 385.",
            "survey_no": "385",
            "village": "Keelathattaparai",
            "expected_crop": "Cotton",
            "expected_stage": "vegetation",
            "gis_acres": 5.600,
            "expected_decision": "ACCEPT",
            "expected_conflict": False,
            "force_escalate": False,
            "simulate_conflict": False
        },

        # ── CATEGORY 4: DOCUMENT-REGISTRY CONFLICTS & DISCREPANCIES (8 Queries) ───
        {
            "id": "BENCH-37",
            "category": "DOCUMENT_EXTENT_DISCREPANCY",
            "query": "Audit Survey 384 against document claims with simulated extent inflation.",
            "survey_no": "384",
            "village": "Keelathattaparai",
            "expected_crop": "Coconut",
            "expected_stage": "full_growth",
            "gis_acres": 10.349,
            "expected_decision": "ABSTAIN",
            "expected_conflict": True,
            "force_escalate": False,
            "simulate_conflict": True
        },
        {
            "id": "BENCH-38",
            "category": "DOCUMENT_EXTENT_DISCREPANCY",
            "query": "Verify Survey 381 with simulated claimant ownership mismatch.",
            "survey_no": "381",
            "village": "Keelathattaparai",
            "expected_crop": "Rice (Paddy)",
            "expected_stage": "full_growth",
            "gis_acres": 4.210,
            "expected_decision": "ABSTAIN",
            "expected_conflict": True,
            "force_escalate": False,
            "simulate_conflict": True
        },
        {
            "id": "BENCH-39",
            "category": "DOCUMENT_EXTENT_DISCREPANCY",
            "query": "Audit Survey 174 with conflicting document schedule details.",
            "survey_no": "174",
            "village": "Keelathattaparai",
            "expected_crop": "Maize",
            "expected_stage": "vegetation",
            "gis_acres": 6.240,
            "expected_decision": "ABSTAIN",
            "expected_conflict": True,
            "force_escalate": False,
            "simulate_conflict": True
        },
        {
            "id": "BENCH-40",
            "category": "DOCUMENT_EXTENT_DISCREPANCY",
            "query": "Verify Survey 387 with artificial discrepancy in documented boundaries.",
            "survey_no": "387",
            "village": "Keelathattaparai",
            "expected_crop": "Sugarcane",
            "expected_stage": "full_growth",
            "gis_acres": 8.500,
            "expected_decision": "ABSTAIN",
            "expected_conflict": True,
            "force_escalate": False,
            "simulate_conflict": True
        },
        {
            "id": "BENCH-41",
            "category": "DOCUMENT_EXTENT_DISCREPANCY",
            "query": "Audit Survey 388 with injected ownership title dispute.",
            "survey_no": "388",
            "village": "Keelathattaparai",
            "expected_crop": "Coconut",
            "expected_stage": "full_growth",
            "gis_acres": 9.400,
            "expected_decision": "ABSTAIN",
            "expected_conflict": True,
            "force_escalate": False,
            "simulate_conflict": True
        },
        {
            "id": "BENCH-42",
            "category": "DOCUMENT_EXTENT_DISCREPANCY",
            "query": "Verify Survey 385 with simulated gazette acreage conflict.",
            "survey_no": "385",
            "village": "Keelathattaparai",
            "expected_crop": "Cotton",
            "expected_stage": "vegetation",
            "gis_acres": 5.600,
            "expected_decision": "ABSTAIN",
            "expected_conflict": True,
            "force_escalate": False,
            "simulate_conflict": True
        },
        {
            "id": "BENCH-43",
            "category": "DOCUMENT_EXTENT_DISCREPANCY",
            "query": "Audit Survey 386 with simulated title conflict between document and registry.",
            "survey_no": "386",
            "village": "Keelathattaparai",
            "expected_crop": "Groundnut",
            "expected_stage": "vegetation",
            "gis_acres": 6.750,
            "expected_decision": "ABSTAIN",
            "expected_conflict": True,
            "force_escalate": False,
            "simulate_conflict": True
        },
        {
            "id": "BENCH-44",
            "category": "DOCUMENT_EXTENT_DISCREPANCY",
            "query": "Audit Survey 81 with simulated conflicting claimant identity.",
            "survey_no": "81",
            "village": "Keelathattaparai",
            "expected_crop": "Sorghum",
            "expected_stage": "vegetation",
            "gis_acres": 2.496,
            "expected_decision": "ABSTAIN",
            "expected_conflict": True,
            "force_escalate": False,
            "simulate_conflict": True
        },

        # ── CATEGORY 5: UNSUPPORTED PARCELS & SUBDIVISIONS (6 Queries) ────────────
        {
            "id": "BENCH-45",
            "category": "UNSUPPORTED_AND_ABSTAIN",
            "query": "Audit non-existent Survey 9999 in Keelathattaparai village.",
            "survey_no": "9999",
            "village": "Keelathattaparai",
            "expected_crop": None,
            "expected_stage": None,
            "gis_acres": None,
            "expected_decision": "ABSTAIN",
            "expected_conflict": True,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-46",
            "category": "UNSUPPORTED_AND_ABSTAIN",
            "query": "Verify unrecorded cadastral parcel Survey 9998 in Keelathattaparai.",
            "survey_no": "9998",
            "village": "Keelathattaparai",
            "expected_crop": None,
            "expected_stage": None,
            "gis_acres": None,
            "expected_decision": "ABSTAIN",
            "expected_conflict": True,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-47",
            "category": "UNSUPPORTED_AND_ABSTAIN",
            "query": "Audit fictitious subdivision Survey 384/99 in Keelathattaparai under refuse-to-substitute policy.",
            "survey_no": "384/99",
            "village": "Keelathattaparai",
            "expected_crop": None,
            "expected_stage": None,
            "gis_acres": None,
            "expected_decision": "ABSTAIN",
            "expected_conflict": True,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-48",
            "category": "UNSUPPORTED_AND_ABSTAIN",
            "query": "Check unrecorded subdivision Survey 176/99 in Keelathattaparai.",
            "survey_no": "176/99",
            "village": "Keelathattaparai",
            "expected_crop": None,
            "expected_stage": None,
            "gis_acres": None,
            "expected_decision": "ABSTAIN",
            "expected_conflict": True,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-49",
            "category": "UNSUPPORTED_AND_ABSTAIN",
            "query": "Provide crop health and general advisory without specifying any survey number or village.",
            "survey_no": None,
            "village": "Keelathattaparai",
            "expected_crop": None,
            "expected_stage": None,
            "gis_acres": None,
            "expected_decision": "ABSTAIN",
            "expected_conflict": True,
            "force_escalate": False,
            "simulate_conflict": False
        },
        {
            "id": "BENCH-50",
            "category": "UNSUPPORTED_AND_ABSTAIN",
            "query": "Audit unknown agricultural land plot in Keelathattaparai with missing cadastral record.",
            "survey_no": "9995",
            "village": "Keelathattaparai",
            "expected_crop": None,
            "expected_stage": None,
            "gis_acres": None,
            "expected_decision": "ABSTAIN",
            "expected_conflict": True,
            "force_escalate": False,
            "simulate_conflict": False
        }
    ]
    
    assert len(queries) == 50, f"Expected exactly 50 benchmark queries, got {len(queries)}"
    return queries

def save_benchmark_queries_json(output_path: str = None) -> str:
    """Serializes the 50 benchmark queries into JSON for external evaluation."""
    if output_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        output_path = os.path.join(base_dir, "data", "benchmark_50_queries.json")
    
    queries = get_benchmark_queries()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "benchmark_name": "FARMSYNC 50-Query Multimodal Cadastral Benchmark",
            "total_queries": len(queries),
            "version": "2.0.0",
            "categories": {
                "CONFIDENT_GROUNDED": 22,
                "PERCEPTION_ESCALATION": 8,
                "BUFFER_AND_ACCESS": 6,
                "DOCUMENT_EXTENT_DISCREPANCY": 8,
                "UNSUPPORTED_AND_ABSTAIN": 6
            },
            "queries": queries
        }, f, indent=2)
    return output_path
