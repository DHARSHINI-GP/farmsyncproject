"""
Tests verifying that parcels without a prior status record are explicitly displayed
as 'Not verified' rather than defaulting to 'Verified'.
"""

import os
import json
import pytest
from fastapi.testclient import TestClient

from farmsync.server import app, STATUS_MAP


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_parcels_endpoint_unaudited_surveys_are_not_verified(client):
    """
    [P2 AUDIT TEST]
    Verifies that /api/parcels does NOT default unknown or unaudited surveys to 'Verified'.
    Unrecorded surveys must have status: 'Not verified' and badge: 'neutral'.
    """
    resp = client.get("/api/parcels")
    assert resp.status_code == 200
    data = resp.json()
    assert "parcels" in data
    assert len(data["parcels"]) > 0

    known_audited_surveys = set(STATUS_MAP.keys())
    unaudited_found = False

    for p in data["parcels"]:
        s_no = str(p["survey_no"])
        if s_no in known_audited_surveys:
            expected_status = STATUS_MAP[s_no]["status"]
            assert p["status"] == expected_status
        else:
            unaudited_found = True
            # STRICT REQUIREMENT: Must not default to 'Verified'
            assert p["status"] in ("Not verified", "Unknown"), (
                f"Survey {s_no} has no status record but was returned as '{p['status']}' instead of 'Not verified'!"
            )
            assert p["status"] != "Verified"
            assert p["badge"] == "neutral"

    assert unaudited_found, "Expected to find unaudited surveys in the parcel list"


def test_geojson_all_parcels_unaudited_surveys_are_not_verified(client):
    """
    [P2 AUDIT TEST]
    Verifies that /api/geojson/all-parcels does NOT default unknown or unaudited surveys to 'Verified'.
    Feature properties for unrecorded surveys must have status: 'Not verified' and badge: 'neutral'.
    """
    resp = client.get("/api/geojson/all-parcels")
    assert resp.status_code == 200
    geojson_data = resp.json()
    assert "features" in geojson_data
    assert len(geojson_data["features"]) > 0

    known_audited_surveys = set(STATUS_MAP.keys())
    unaudited_features_found = False

    for feat in geojson_data["features"]:
        props = feat.get("properties", {})
        s_no = str(props.get("survey_no", ""))
        if s_no in known_audited_surveys:
            expected_status = STATUS_MAP[s_no]["status"]
            assert props.get("status") == expected_status
        else:
            unaudited_features_found = True
            status = props.get("status")
            assert status in ("Not verified", "Unknown"), (
                f"GeoJSON feature for survey {s_no} has no status record but was returned as '{status}'!"
            )
            assert status != "Verified"
            assert props.get("badge") == "neutral"

    assert unaudited_features_found, "Expected to find unaudited surveys in GeoJSON features"
