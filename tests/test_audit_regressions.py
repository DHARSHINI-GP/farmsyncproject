"""Regression cases found during the deployment readiness audit."""
import pytest
from fastapi.testclient import TestClient

from farmsync.server import app, ai_engine, orchestrator
from farmsync.router.compiler import TaskGraphCompiler


@pytest.fixture
def offline(monkeypatch):
    monkeypatch.delenv("FARMSYNC_API_KEY", raising=False)
    monkeypatch.setattr(ai_engine, "bedrock_client", None)
    monkeypatch.setattr(orchestrator.location_engine, "client", None)
    monkeypatch.setattr(orchestrator.vision, "bedrock_client", None)
    return TestClient(app)


def test_question_survey_overrides_map_selection(offline):
    result = offline.post("/api/ai/query", json={
        "query": "Inspect Survey 9999", "survey_no": "384"
    })
    assert result.status_code == 200
    assert result.json()["target_survey_no"] == "9999"
    assert result.json()["extracted_attributes"]["gis_area_acres"] is None


def test_buffer_query_does_not_claim_vision_execution(offline):
    result = offline.post("/api/ai/query", json={"query": "Check waterbody buffer for Survey 384"})
    assert result.status_code == 200
    assert "No field photograph was analyzed" in result.json()["thought_process"][3]


def test_subdivision_detail_route(offline):
    assert offline.get("/api/parcel/384/1").status_code == 200
    assert offline.get("/api/location/geofence/384/1").status_code == 200


@pytest.mark.parametrize("path", ["../../README.md", "../../.env", "../outside.pdf"])
def test_document_extraction_rejects_paths_outside_library(path):
    result = orchestrator.docs.extract_document_claims(path, "384")
    assert result["found"] is False
    assert result["status"] == "DOCUMENT_PATH_NOT_ALLOWED"


def test_discrepancy_workflow_uses_supported_contracts():
    graph = TaskGraphCompiler().compile("Find extent difference for Survey 384")
    assert graph.workflow_type == "LAND_DISCREPANCY_INTELLIGENCE"
    tasks = graph.topological_sort()
    assert any(t.subtask_type == "DATABASE_JOIN" for t in tasks)
    assert not any("doc_parcels" in t.outputs for t in tasks)


def test_gis_variance_is_not_registry_variance(offline, monkeypatch):
    monkeypatch.setattr(orchestrator.docs, "extract_document_claims", lambda **kwargs: {
        "found": True, "survey_no": "384", "claimed_extent_acres": 1.0,
        "extracted_owner": "Test claimant", "document_source": "fixture.pdf"
    })
    monkeypatch.setattr(orchestrator.docs, "cross_check_registry", lambda claims: {
        "found": True, "extent_diff_pct": 0.0, "owner_match": True
    })
    result = orchestrator.execute_request("Inspect Survey 384")
    expected = orchestrator.spatial.verify_extent("384", 1.0)["discrepancy_percentage"]
    assert result["verified_result_object"]["extracted_attributes"]["extent_difference_pct"] == expected
    assert expected > 5


@pytest.mark.parametrize("path", ["/api/ai/query", "/api/orchestrate", "/api/location/route"])
def test_cost_bearing_endpoints_require_key(path, monkeypatch):
    monkeypatch.setenv("FARMSYNC_API_KEY", "audit-test-key")
    client = TestClient(app)
    result = client.post(path, json={"query": "Inspect Survey 384", "survey_no": "384"})
    assert result.status_code == 401


def test_non_string_key_returns_unauthorized(monkeypatch):
    monkeypatch.setenv("FARMSYNC_API_KEY", "audit-test-key")
    result = TestClient(app).post("/api/orchestrate", json={"query": "Inspect", "api_key": {"bad": "type"}})
    assert result.status_code == 401


def test_invalid_coordinates_rejected(offline):
    result = offline.post("/api/location/route", json={"survey_no": "384", "origin_lat": 100})
    assert result.status_code == 422


def test_repeated_survey_number_is_not_arbitrarily_verified(offline):
    assert orchestrator.spatial.get_parcel("176") is None
    checks = orchestrator.spatial.check_constraints("176")
    assert checks["deterministic_spatial_verified"] is False
    result = offline.post("/api/orchestrate", json={"query": "Inspect Survey 176"})
    assert result.status_code == 200
    assert result.json()["verified_result_object"]["extracted_attributes"]["gis_area_acres"] is None


def test_map_uses_individual_polygon_areas(offline):
    features = offline.get("/api/geojson/all-parcels").json()["features"]
    repeated = [f for f in features if str(f["properties"]["survey_no"]) == "176"]
    assert len(repeated) == 3
    assert len({f["properties"]["area_acres"] for f in repeated}) > 1
    assert all(f["properties"]["identity_ambiguous"] for f in repeated)


def test_repeated_surveys_resolve_by_full_feature_identity(offline):
    features = offline.get("/api/geojson/all-parcels").json()["features"]
    records = [f["properties"] for f in features if str(f["properties"]["survey_no"]) == "176"]
    assert len({record["parcel_id"] for record in records}) == 3
    for record in records:
        response = offline.get("/api/parcel/" + record["parcel_id"])
        assert response.status_code == 200
        assert response.json()["parcel"]["village"] == record["vil_name"]
        audit = offline.post("/api/orchestrate", json={"query": "Check waterbody buffer for Survey 176", "parcel_id": record["parcel_id"]})
        assert audit.status_code == 200
        assert audit.json()["verified_result_object"]["village"] == record["vil_name"]
        assert audit.json()["verified_result_object"]["extracted_attributes"]["gis_area_acres"] == record["area_acres"]


def test_all_polygon_records_are_browsable(offline):
    data = offline.get("/api/parcels").json()
    assert data["total_parcels"] == len(data["parcels"]) == 396
    assert len({p["parcel_id"] for p in data["parcels"]}) == 396


def test_photo_survey_number_does_not_imply_spatial_match(offline):
    photo = orchestrator.vision.get_image_for_survey("384", parcel=orchestrator.spatial.get_parcel("384"))
    assert photo is None
    result = offline.post("/api/ai/query", json={"query": "Inspect Survey 384"}).json()
    assert result["extracted_attributes"]["predicted_crop"] is None
    assert result["extracted_attributes"]["photo_association_verified"] is False


def test_challenge_datasets_not_public_on_network(monkeypatch):
    monkeypatch.delenv("FARMSYNC_API_KEY", raising=False)
    client = TestClient(app, client=("192.168.1.105", 1234))
    for path in ("/api/parcels", "/api/geojson/all-parcels", "/api/documents/list", "/api/images"):
        assert client.get(path).status_code == 401


def test_image_backslash_traversal_is_not_served(offline):
    assert offline.get("/api/image/..%5C..%5C..%5C.env").status_code == 404


def test_runtime_credentials_disabled_by_default(offline, monkeypatch):
    monkeypatch.delenv("FARMSYNC_ALLOW_RUNTIME_CREDENTIALS", raising=False)
    result = offline.post("/api/settings/aws", json={"access_key_id": "key", "secret_access_key": "secret"})
    assert result.status_code == 403
