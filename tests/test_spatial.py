import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from farmsync.spatial.engine import SpatialEngine

@pytest.fixture(scope="module")
def engine():
    return SpatialEngine()

def test_survey_parcels_indexed(engine):
    surveys = engine.list_surveys()
    assert len(surveys) > 0, "No surveys found!"

def test_survey_384_geometry(engine):
    p = engine.get_parcel("384")
    assert p is not None, "Survey 384 not found!"
    assert p["area_acres"] > 0
    assert "centroid" in p

def test_constraints_calculation_50m_buffer(engine):
    """Validates 50m default waterbody buffer, distance calculations, and engine metadata."""
    c = engine.check_constraints("384")
    assert "distance_to_waterbody_meters" in c
    assert "distance_to_road_meters" in c
    assert "distance_to_substation_meters" in c
    # Proposal Section 4.2 & 7.2 requirement: 50m waterbody buffer
    assert c["waterbody_buffer_threshold_meters"] == 50.0
    assert c["waterbody_buffer_50m_compliant"] is True
    assert c["waterbody_buffer_conflict"] is False
    assert c["spatial_engine"] == "GeoPandas_Shapely_UTM44N"

def test_cadastral_containment_verification(engine):
    """Validates true Shapely topological validity and cadastral boundary containment."""
    c = engine.check_constraints("384")
    assert c["cadastral_containment_valid"] is True
    assert c["geometry_valid"] is True

    # Unknown survey must not be asserted as contained
    c_unknown = engine.check_constraints("9999_UNKNOWN")
    assert c_unknown["cadastral_containment_valid"] is False
    assert c_unknown["geometry_valid"] is False

def test_extent_verification_match(engine):
    v_match = engine.verify_extent("384", claimed_acres=10.34)
    assert v_match["verification_status"] == "MATCH"

def test_extent_verification_discrepancy(engine):
    v_mismatch = engine.verify_extent("384", claimed_acres=12.5)
    assert v_mismatch["verification_status"] == "DISCREPANCY_FLAGGED"


def main():
    print("Testing SpatialEngine...")
    eng = SpatialEngine()
    test_survey_parcels_indexed(eng)
    test_survey_384_geometry(eng)
    test_constraints_calculation_50m_buffer(eng)
    test_cadastral_containment_verification(eng)
    test_extent_verification_match(eng)
    test_extent_verification_discrepancy(eng)
    print("ALL SPATIAL TESTS PASSED!")


if __name__ == "__main__":
    main()
