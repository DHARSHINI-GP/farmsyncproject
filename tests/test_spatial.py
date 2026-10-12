import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from farmsync.spatial.engine import SpatialEngine

def main():
    print("Testing SpatialEngine...")
    engine = SpatialEngine()
    surveys = engine.list_surveys()
    print(f"Total surveyed parcels: {len(surveys)}")
    assert len(surveys) > 0, "No surveys found!"

    # Test Survey 384
    p = engine.get_parcel("384")
    assert p is not None, "Survey 384 not found!"
    print(f"Parcel 384: {p['village']} | {p['area_acres']} acres | Centroid: {p['centroid']}")

    # Test constraints
    c = engine.check_constraints("384")
    print(f"Constraints 384: Water={c['distance_to_waterbody_meters']}m, Road={c['distance_to_road_meters']}m, Substation={c['distance_to_substation_meters']}m")

    # Test extent check (matching)
    v_match = engine.verify_extent("384", claimed_acres=10.34)
    print(f"Extent 10.34 acres match: status={v_match['verification_status']}, diff={v_match['discrepancy_percentage']}%")
    assert v_match["verification_status"] == "MATCH"

    # Test extent check (mismatch >5%)
    v_mismatch = engine.verify_extent("384", claimed_acres=12.5)
    print(f"Extent 12.5 acres mismatch: status={v_mismatch['verification_status']}, diff={v_mismatch['discrepancy_percentage']}%")
    assert v_mismatch["verification_status"] == "DISCREPANCY_FLAGGED"

    print("ALL SPATIAL TESTS PASSED!")

if __name__ == "__main__":
    main()
