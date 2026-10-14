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

def test_constraints_calculation(engine):
    c = engine.check_constraints("384")
    assert "distance_to_waterbody_meters" in c
    assert "distance_to_road_meters" in c
    assert "distance_to_substation_meters" in c

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
    test_constraints_calculation(eng)
    test_extent_verification_match(eng)
    test_extent_verification_discrepancy(eng)
    print("ALL SPATIAL TESTS PASSED!")


if __name__ == "__main__":
    main()
