import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from farmsync.trust.trust_score import TrustEngine


@pytest.fixture(scope="module")
def trust_engine():
    return TrustEngine()


def test_trust_weights_sum_to_one(trust_engine):
    """
    Validates Section 3.2 constraint: sum(w_i, i=1..5) == 1.00
    with w1=0.15, w2=0.25, w3=0.25, w4=0.25, w5=0.10, w6=0.20.
    """
    pos_weights_sum = (
        trust_engine.w1_calib +
        trust_engine.w2_coverage +
        trust_engine.w3_consistency +
        trust_engine.w4_det_val +
        trust_engine.w5_validity
    )
    assert round(pos_weights_sum, 4) == 1.0000
    assert trust_engine.w1_calib == 0.15
    assert trust_engine.w2_coverage == 0.25
    assert trust_engine.w3_consistency == 0.25
    assert trust_engine.w4_det_val == 0.25
    assert trust_engine.w5_validity == 0.10
    assert trust_engine.w6_conflict == 0.20
    assert trust_engine.accept_threshold == 0.85
    assert trust_engine.escalate_threshold == 0.70


def test_proposal_benchmark_survey_384(trust_engine):
    """
    Validates that default evidence signals for Survey 384 produce exactly
    the proposal's reported benchmark score of FTS = 0.942 and ACCEPT verdict.
    """
    valid_payload = {
        "survey_number": "384",
        "village": "Keelathattaparai",
        "extracted_attributes": {
            "registered_owner": "Ramesh G",
            "gis_area_acres": 10.349,
            "predicted_crop": "Coconut",
            "growth_stage": "full_growth"
        },
        "deterministic_spatial_checks": {
            "spatial_extent_verified": True,
            "waterbody_buffer_compliant": True
        }
    }

    res = trust_engine.evaluate_trust(
        vision_confidence=0.99,
        is_supported_crop=True,
        doc_registry_match=True,
        spatial_extent_match=True,
        waterbody_conflict=False,
        has_field_photo=True,
        has_land_doc=True,
        has_registry=True,
        output_payload=valid_payload
    )

    assert res["fts_score"] == 0.942
    assert res["decision"] == "ACCEPT"
    assert res["breakdown"]["calibration"] == 0.92
    assert res["breakdown"]["evidence_coverage"] == 1.00
    assert res["breakdown"]["source_consistency"] == 0.95
    assert res["breakdown"]["deterministic_validation"] == 0.98
    assert res["breakdown"]["output_validity"] == 1.00


def test_vision_confidence_active_modulation(trust_engine):
    """
    Validates that vision_confidence is an active signal that proportionally
    calibrates the historical calibration factor C_cal.
    """
    # High confidence (0.99)
    res_high = trust_engine.evaluate_trust(
        vision_confidence=0.99,
        is_supported_crop=True,
        doc_registry_match=True,
        spatial_extent_match=True,
        waterbody_conflict=False,
        has_field_photo=True,
        has_land_doc=True,
        has_registry=True
    )
    assert res_high["breakdown"]["calibration"] == 0.92

    # Medium confidence (0.60)
    res_med = trust_engine.evaluate_trust(
        vision_confidence=0.60,
        is_supported_crop=True,
        doc_registry_match=True,
        spatial_extent_match=True,
        waterbody_conflict=False,
        has_field_photo=True,
        has_land_doc=True,
        has_registry=True
    )
    assert res_med["breakdown"]["calibration"] < 0.92
    assert res_med["fts_score"] < res_high["fts_score"]

    # Zero confidence / Missing photo
    res_zero = trust_engine.evaluate_trust(
        vision_confidence=0.0,
        is_supported_crop=True,
        doc_registry_match=True,
        spatial_extent_match=True,
        waterbody_conflict=False,
        has_field_photo=False,
        has_land_doc=True,
        has_registry=True
    )
    assert res_zero["breakdown"]["calibration"] == 0.0


def test_jsonschema_output_validity(trust_engine):
    """
    Validates that Output Validity uses real jsonschema validation:
    - 1.00 when payload conforms strictly to OUTPUT_SCHEMA
    - 0.00 when required fields are missing or types are violated
    """
    # Valid payload
    valid_payload = {
        "survey_number": "384",
        "village": "Keelathattaparai",
        "extracted_attributes": {
            "registered_owner": "Ramesh G",
            "gis_area_acres": 10.349,
            "predicted_crop": "Coconut",
            "growth_stage": "full_growth"
        },
        "deterministic_spatial_checks": {
            "spatial_extent_verified": True,
            "waterbody_buffer_compliant": True
        }
    }
    assert trust_engine.validate_output_schema(valid_payload) == 1.00

    # Invalid payload (missing required field 'village' and 'extracted_attributes')
    invalid_payload = {
        "survey_number": "384"
    }
    assert trust_engine.validate_output_schema(invalid_payload) == 0.00


def test_injected_conflict_abstention(trust_engine):
    """
    Validates that contradictory document-registry records drop FTS below 0.70
    and trigger explicit ABSTAIN (Human Review).
    """
    res = trust_engine.evaluate_trust(
        vision_confidence=0.99,
        is_supported_crop=True,
        doc_registry_match=False,  # Conflict!
        spatial_extent_match=True,
        waterbody_conflict=False,
        has_field_photo=True,
        has_land_doc=True,
        has_registry=True
    )
    assert res["decision"] == "ABSTAIN"
    assert res["fts_score"] < 0.70


def test_out_of_distribution_escalation(trust_engine):
    """
    Validates that unsupported / OOD crops drop FTS into [0.70, 0.85),
    triggering bounded ESCALATE to secondary teacher verification.
    """
    res = trust_engine.evaluate_trust(
        vision_confidence=0.45,
        is_supported_crop=False,  # OOD!
        doc_registry_match=True,
        spatial_extent_match=True,
        waterbody_conflict=False,
        has_field_photo=True,
        has_land_doc=True,
        has_registry=True
    )
    assert res["decision"] == "ESCALATE"
    assert 0.70 <= res["fts_score"] < 0.85


def main():
    print("Testing TrustEngine...")
    eng = TrustEngine()
    test_trust_weights_sum_to_one(eng)
    test_proposal_benchmark_survey_384(eng)
    test_vision_confidence_active_modulation(eng)
    test_jsonschema_output_validity(eng)
    test_injected_conflict_abstention(eng)
    test_out_of_distribution_escalation(eng)
    print("ALL TRUST TESTS PASSED PERFECTLY!")


if __name__ == "__main__":
    main()
