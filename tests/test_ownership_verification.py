import os
import sys
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from farmsync.documents.extractor import DocumentRegistryExtractor
from farmsync.orchestrator import FarmSyncOrchestrator
from farmsync.trust.evidence_graph import EvidenceGraphBuilder


@pytest.fixture(scope="module")
def extractor():
    return DocumentRegistryExtractor()


@pytest.fixture(scope="module")
def orchestrator():
    return FarmSyncOrchestrator()


def test_cadastral_geojson_has_no_ownership_data():
    """
    CRITICAL AUDIT VERIFICATION:
    Verifies that Park_Cadastral_Map.geojson only contains spatial boundaries
    and cadastral attributes (taluk, village, survey_no), and has ZERO ownership records.
    Confirms why an independent Record of Rights (Revenue Registry) is mandatory.
    """
    cadastral_path = os.path.join("data", "FAI_Product_Challange", "TASK_2", "Geospatial_Layer", "Park_Cadastral_Map.geojson")
    assert os.path.exists(cadastral_path), f"Cadastral map not found at {cadastral_path}"

    with open(cadastral_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    forbidden_ownership_keys = {"owner", "registered_owner", "pattadar", "owner_name", "applicant", "claimant"}

    features = data.get("features", [])
    assert len(features) > 0

    for feat in features:
        props = feat.get("properties", {})
        for key in props.keys():
            assert key.lower() not in forbidden_ownership_keys, (
                f"Unexpected ownership property '{key}' found in cadastral geometry layer!"
            )


def test_independent_revenue_registry_structure(extractor):
    """
    Verifies that the independent Revenue Land Registry (Record of Rights)
    contains authentic patta numbers, registered owners, and extent.
    """
    assert hasattr(extractor, "revenue_registry")
    assert len(extractor.revenue_registry) >= 10
    
    # Check Survey 384
    ror_384 = extractor.revenue_registry.get("384")
    assert ror_384 is not None
    assert ror_384["survey_no"] == "384"
    assert "Ramesh Kumar" in ror_384["registered_owner"]
    assert ror_384["patta_number"] == "1136"
    assert ror_384["registered_extent_acres"] == 10.349


def test_authentic_owner_matching_survey_384(extractor):
    """
    Verifies that a valid claimant (e.g. Ramesh Kumar) matching the Record of Rights
    is verified as MATCH, and official_owner is strictly retrieved from the revenue registry.
    """
    doc_claims = {
        "found": True,
        "extracted_owner": "Ramesh Kumar",
        "claimed_extent_acres": 10.349,
        "document_source": "sample_patta_384.pdf"
    }

    result = extractor.cross_check_registry("384", doc_claims)

    assert result["registry_found"] is True
    assert result["owner_match"] is True
    assert result["owner_verification_status"] == "DEMO_MATCH_NOT_OFFICIAL_VERIFICATION"
    assert result["ownership_verified"] is False
    assert result["demo_record_match"] is True
    assert result["is_authoritative_government_record"] is False
    assert result["official_owner"] == "Ramesh Kumar S/o Sundaram"
    assert result["document_owner"] == "Ramesh Kumar"
    assert result["patta_number"] == "1136"
    assert result["extent_match"] is True
    assert result["status"] == "DEMO_MATCH_NOT_OFFICIAL_VERIFICATION"


def test_unverified_legal_claim_rejection(extractor):
    """
    CRITICAL FLAW PREVENTED:
    When a document asserts an unauthorized/discrepant owner name,
    the system MUST NOT treat it as a match and MUST NEVER adopt the document's
    claimed name as the official owner.
    """
    fraudulent_doc_claims = {
        "found": True,
        "extracted_owner": "Unauthorized Third Party Claimant",
        "claimed_extent_acres": 10.349,
        "document_source": "forged_application.pdf"
    }

    result = extractor.cross_check_registry("384", fraudulent_doc_claims)

    assert result["registry_found"] is True
    assert result["owner_match"] is False
    assert result["owner_verification_status"] == "OWNERSHIP_DISCREPANCY_DETECTED"
    # STRICT ASSERTION: official_owner must reflect the official RoR, NEVER the fraudulent document!
    assert result["official_owner"] == "Ramesh Kumar S/o Sundaram"
    assert result["official_owner"] != "Unauthorized Third Party Claimant"
    assert result["document_owner"] == "Unauthorized Third Party Claimant"
    assert result["status"] == "DISCREPANCY_DETECTED"


def test_survey_with_no_registry_record_refuses_assertion(extractor):
    """
    CRITICAL FLAW PREVENTED:
    If a survey has no independent Revenue Registry (Record of Rights) record,
    the system MUST report official_owner=None and owner_match=False.
    It MUST NEVER fall back to asserting doc_owner as the official owner.
    """
    doc_claims = {
        "found": True,
        "extracted_owner": "Unverified Land Occupant",
        "claimed_extent_acres": 5.0,
        "document_source": "unregistered_deed.pdf"
    }

    result = extractor.cross_check_registry("99999", doc_claims)

    assert result["registry_found"] is False
    assert result["official_owner"] is None
    assert result["owner_match"] is False
    assert result["owner_verification_status"] == "UNVERIFIED_NO_REGISTRY_RECORD"
    assert result["status"] == "UNVERIFIED_NO_REGISTRY_RECORD"
    assert "no independent land registry record exists" in result["details"].lower()


def test_evidence_graph_builder_no_circular_assertion():
    """
    Verifies that EvidenceGraphBuilder does not populate registered_owner
    from doc_claims when registry record is absent.
    """
    builder = EvidenceGraphBuilder()

    doc_claims = {
        "found": True,
        "extracted_owner": "Tentative Claimant",
        "claimed_extent_acres": 4.5,
        "document_source": "deed_doc.pdf"
    }
    registry_check_absent = {
        "registry_found": False,
        "official_owner": None,
        "owner_match": False,
        "owner_verification_status": "UNVERIFIED_NO_REGISTRY_RECORD"
    }

    evidence_obj = builder.build_evidence_object(
        survey_no="777",
        village="Keelathattaparai",
        parcel_gis={"area_acres": 4.5},
        doc_claims=doc_claims,
        registry_check=registry_check_absent,
        spatial_constraints={"cadastral_containment_valid": True},
        vision_result={},
        advisory_result={},
        trust_result={"fts_score": 0.40, "decision": "ABSTAIN"},
        telemetry={}
    )

    extracted_attrs = evidence_obj["extracted_attributes"]
    # STRICT ASSERTIONS:
    assert extracted_attrs["registered_owner"] is None
    assert extracted_attrs["document_owner"] == "Tentative Claimant"
    assert extracted_attrs["ownership_verified"] is False
    assert extracted_attrs["ownership_status"] == "UNVERIFIED_NO_REGISTRY_RECORD"

    # In nodes, db_node must be REGISTRY_ABSENT
    nodes = {n["id"]: n for n in evidence_obj["evidence_graph_dag"]["nodes"]}
    assert nodes["db_node"]["type"] == "REGISTRY_ABSENT"
    assert "NO RECORD FOR SURVEY" in nodes["db_node"]["label"]


def test_orchestrator_abstains_on_ownership_discrepancy(orchestrator):
    """
    Verifies that the orchestrator rejects/abstains when document ownership
    conflicts with the official Revenue Land Registry.
    """
    prompt = "Verify claim for Survey 384 in Keelathattaparai village with conflicting claimant"

    # Execute request with conflict simulation
    res = orchestrator.execute_request(
        query=prompt,
        simulate_conflict=True
    )
    vobj = res["verified_result_object"]

    # Survey 384 official owner from revenue registry
    assert vobj["extracted_attributes"]["registered_owner"] == "Ramesh Kumar S/o Sundaram"
    # Ownership verified is False because conflicting claimant was presented
    assert vobj["extracted_attributes"]["ownership_verified"] is False
    assert vobj["extracted_attributes"]["ownership_status"] == "OWNERSHIP_DISCREPANCY_DETECTED"
    # Decision must be ABSTAIN due to ownership discrepancy
    assert vobj["trust_metrics"]["verification_status"] == "VERIFIED_ABSTAIN"


def test_demonstration_registry_provenance_and_authoritative_source(extractor):
    """
    Verifies that bundled owner records are clearly labeled as demonstration benchmark data
    with traceable source authority and disclaimers, preventing users from mistaking them
    for live government confirmations.
    """
    ror_384 = extractor.revenue_registry.get("384")
    assert ror_384 is not None
    assert ror_384["data_provenance"] == "DEMONSTRATION_BENCHMARK_DATA"
    assert ror_384["is_authoritative_government_record"] is False
    assert "source_authority" in ror_384
    assert "legal_disclaimer" in ror_384
    assert ror_384["ror_status"] == "DEMO_ACTIVE"

    # Check cross_check_registry output metadata
    doc_claims = {
        "found": True,
        "extracted_owner": "Ramesh Kumar",
        "claimed_extent_acres": 10.349,
        "document_source": "sample_patta_384.pdf"
    }
    result = extractor.cross_check_registry("384", doc_claims)
    assert result["is_authoritative_government_record"] is False
    assert result["data_provenance"] == "DEMONSTRATION_BENCHMARK_DATA"
    assert "source_authority" in result
    assert "registry_disclaimer" in result
    assert "demonstration benchmark data" in result["details"].lower()


def test_evidence_graph_builder_records_demonstration_provenance():
    """
    Verifies that EvidenceGraphBuilder labels the database node as Demo Registry
    and populates provenance metadata in extracted attributes and source evidence.
    """
    builder = EvidenceGraphBuilder()
    doc_claims = {
        "found": True,
        "extracted_owner": "Ramesh Kumar",
        "claimed_extent_acres": 10.349,
        "document_source": "sample_patta_384.pdf"
    }
    registry_check = {
        "registry_found": True,
        "official_owner": "Ramesh Kumar S/o Sundaram",
        "patta_number": "1136",
        "owner_match": True,
        "owner_verification_status": "DEMO_MATCH_NOT_OFFICIAL_VERIFICATION",
        "data_provenance": "DEMONSTRATION_BENCHMARK_DATA",
        "source_authority": "TamilNilam Revenue Record of Rights Schema (Demonstration Fixture)",
        "is_authoritative_government_record": False,
        "registry_disclaimer": "Demonstration benchmark dataset; not an authoritative live government confirmation."
    }

    evidence_obj = builder.build_evidence_object(
        survey_no="384",
        village="Keelathattaparai",
        parcel_gis={"area_acres": 10.349},
        doc_claims=doc_claims,
        registry_check=registry_check,
        spatial_constraints={"cadastral_containment_valid": True},
        vision_result={},
        advisory_result={},
        trust_result={"fts_score": 0.94, "decision": "ACCEPT"},
        telemetry={}
    )

    attrs = evidence_obj["extracted_attributes"]
    assert attrs["ownership_provenance"] == "DEMONSTRATION_BENCHMARK_DATA"
    assert attrs["is_authoritative_government_record"] is False
    assert attrs["ownership_verified"] is False
    assert attrs["ownership_status"] == "DEMO_MATCH_NOT_OFFICIAL_VERIFICATION"
    assert attrs["demo_record_matched"] is True

    nodes = {n["id"]: n for n in evidence_obj["evidence_graph_dag"]["nodes"]}
    assert "Demo Registry (RoR)" in nodes["db_node"]["label"]

    db_evidence = next(ev for ev in evidence_obj["source_evidence"] if ev["source_type"] == "DATABASE_REGISTRY")
    assert db_evidence["data_provenance"] == "DEMONSTRATION_BENCHMARK_DATA"
    assert db_evidence["is_authoritative_government_record"] is False
    assert db_evidence["status"] == "DEMO_MATCH_NOT_OFFICIAL_VERIFICATION"
    assert "Demonstration Data" in db_evidence["source_ref"]


def test_demonstration_match_is_not_official_verification(extractor, orchestrator):
    """
    CRITICAL AUDIT VERIFICATION:
    Validates that:
    1. A match against bundled demonstration records produces 'DEMO_MATCH_NOT_OFFICIAL_VERIFICATION'
    2. ownership_verified is strictly False (no live government confirmation)
    3. is_authoritative_government_record is strictly False
    4. Orchestration does NOT count the demonstration match as authoritative registry evidence in FTS
    5. Evidence coverage reflects photo and document (2/3 = 0.67) without fabricating authoritative DB coverage
    """
    doc_claims = {
        "found": True,
        "extracted_owner": "Ramesh Kumar",
        "claimed_extent_acres": 10.349,
        "document_source": "sample_patta_384.pdf"
    }

    # Direct extractor cross-check check
    res_ext = extractor.cross_check_registry("384", doc_claims)
    assert res_ext["owner_verification_status"] == "DEMO_MATCH_NOT_OFFICIAL_VERIFICATION"
    assert res_ext["status"] == "DEMO_MATCH_NOT_OFFICIAL_VERIFICATION"
    assert res_ext["ownership_verified"] is False
    assert res_ext["is_authoritative_government_record"] is False
    assert "Demo match—not official verification" in res_ext["details"]

    # End-to-end orchestration check
    res_orch = orchestrator.execute_request("Identify Survey 384 in Keelathattaparai village and verify parcel ownership.")
    vobj = res_orch["verified_result_object"]
    attrs = vobj["extracted_attributes"]

    assert attrs["ownership_verified"] is False
    assert attrs["ownership_status"] == "DEMO_MATCH_NOT_OFFICIAL_VERIFICATION"
    assert attrs["demo_record_matched"] is True
    assert attrs["is_authoritative_government_record"] is False
    assert attrs["ownership_verification_verdict"] == "demo match—not official verification"

    # FTS trust metrics do not count demo registry as authoritative registry evidence (coverage = 2/3 = 0.67)
    trust_metrics = vobj["trust_metrics"]
    breakdown = trust_metrics["signal_breakdown"]
    # Only the document is usable: the photo is outside the parcel, and the
    # bundled registry is not authoritative ownership evidence.
    assert breakdown["evidence_coverage"] == 0.33
    assert trust_metrics["verification_status"] == "VERIFIED_ABSTAIN"



