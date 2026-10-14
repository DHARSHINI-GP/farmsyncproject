"""
Tests for farmsync.spatial.amazon_location – verifying honest labelling,
no fabricated geometry, and correct AWS/local source attribution.
"""

import os
import math
import pytest
from unittest.mock import patch, MagicMock

from farmsync.spatial.amazon_location import AmazonLocationServiceEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine_no_aws():
    """Engine with NO AWS credentials → all calls must fall back to local."""
    env_overrides = {
        "AWS_ACCESS_KEY_ID": "",
        "AWS_SECRET_ACCESS_KEY": "",
        "AWS_SESSION_TOKEN": "",
    }
    with patch.dict(os.environ, env_overrides, clear=False):
        eng = AmazonLocationServiceEngine()
        assert eng.client is None, "Client must be None without credentials"
        yield eng


@pytest.fixture
def engine_with_mock_aws():
    """Engine with a mocked boto3 Location client (simulates AWS connected)."""
    eng = AmazonLocationServiceEngine.__new__(AmazonLocationServiceEngine)
    from farmsync.spatial.engine import SpatialEngine
    eng.spatial = SpatialEngine()
    eng.region = "ap-south-1"
    eng.place_index = "FARMSYNC_PlaceIndex"
    eng.route_calculator = "FARMSYNC_RouteCalculator"
    eng.geofence_collection = "FARMSYNC_GeofenceCollection"
    eng.DEFAULT_DEPOT = {
        "name": "Vagaikulam TNAU Agricultural Depot & Substation",
        "latitude": 8.752486,
        "longitude": 77.992336,
        "district": "Thoothukudi",
    }
    eng.client = MagicMock()
    yield eng


# ---------------------------------------------------------------------------
# 1) Status endpoint
# ---------------------------------------------------------------------------

class TestStatus:
    def test_status_no_aws(self, engine_no_aws):
        status = engine_no_aws.get_status()
        assert status["aws_credentials_available"] is False
        assert status["connected"] is False
        assert "Local" in status["tier"] or "no AWS" in status["tier"]
        assert status["place_index"] is None
        assert status["route_calculator"] is None

    def test_status_with_aws(self, engine_with_mock_aws):
        status = engine_with_mock_aws.get_status()
        assert status["aws_credentials_available"] is True
        assert status["connected"] is True
        assert "ap-south-1" in status["tier"]

    def test_tls_verification_enabled(self, engine_no_aws):
        status = engine_no_aws.get_status()
        assert status["tls_verification_enabled"] is True


# ---------------------------------------------------------------------------
# 2) Reverse Geocode – local fallback
# ---------------------------------------------------------------------------

class TestReverseGeocodeLocal:
    def test_source_is_local(self, engine_no_aws):
        res = engine_no_aws.reverse_geocode(8.75, 78.0, survey_no="384")
        assert "LOCAL_REVENUE_INDEX" in res["source"]
        assert "Amazon Location" not in res["source"]
        assert res["aws_credentials_available"] is False

    def test_address_contains_survey(self, engine_no_aws):
        res = engine_no_aws.reverse_geocode(8.75, 78.0, survey_no="384")
        assert "384" in res["formatted_address"]

    def test_address_without_survey(self, engine_no_aws):
        res = engine_no_aws.reverse_geocode(8.75, 78.0)
        assert "Survey" not in res["formatted_address"]


# ---------------------------------------------------------------------------
# 3) Reverse Geocode – AWS path
# ---------------------------------------------------------------------------

class TestReverseGeocodeAWS:
    def test_uses_api_when_available(self, engine_with_mock_aws):
        engine_with_mock_aws.client.search_place_index_for_position.return_value = {
            "Results": [{
                "Place": {
                    "Label": "8°45'N 78°00'E, Keelathattaparai",
                    "Municipality": "Keelathattaparai",
                    "SubRegion": "Thoothukudi",
                    "Region": "Tamil Nadu",
                    "PostalCode": "628103",
                    "Country": "IND",
                }
            }]
        }
        res = engine_with_mock_aws.reverse_geocode(8.75, 78.0, survey_no="384")
        assert "Amazon Location Service" in res["source"]
        assert res["aws_credentials_available"] is True
        engine_with_mock_aws.client.search_place_index_for_position.assert_called_once()

    def test_falls_back_on_api_error(self, engine_with_mock_aws):
        engine_with_mock_aws.client.search_place_index_for_position.side_effect = Exception("API down")
        res = engine_with_mock_aws.reverse_geocode(8.75, 78.0, survey_no="384")
        # Must fall back to local, honestly labelled
        assert "LOCAL_REVENUE_INDEX" in res["source"]
        assert res["aws_credentials_available"] is False


# ---------------------------------------------------------------------------
# 4) Route Calculation – local fallback
# ---------------------------------------------------------------------------

class TestRouteLocal:
    def test_source_is_local_haversine(self, engine_no_aws):
        res = engine_no_aws.calculate_agri_route("384")
        assert res["source"] == "LOCAL_HAVERSINE_ESTIMATE"
        assert res["aws_credentials_available"] is False

    def test_no_fabricated_geometry(self, engine_no_aws):
        res = engine_no_aws.calculate_agri_route("384")
        coords = res["geojson_route"]["coordinates"]
        # Honest straight-line: exactly 2 points (origin, destination)
        assert len(coords) == 2, (
            f"Fallback geometry must be a straight line (2 pts), got {len(coords)}"
        )

    def test_geometry_note_present(self, engine_no_aws):
        res = engine_no_aws.calculate_agri_route("384")
        note = res["geojson_route"].get("note", "")
        assert "straight line" in note.lower() or "NOT" in note

    def test_estimation_method_documented(self, engine_no_aws):
        res = engine_no_aws.calculate_agri_route("384")
        method = res.get("estimation_method", {})
        assert "haversine" in method.get("base", "").lower()
        assert method.get("road_winding_factor") == 1.28
        assert method.get("assumed_speed_kmh") == 28.0

    def test_distance_is_plausible(self, engine_no_aws):
        res = engine_no_aws.calculate_agri_route("384")
        # Depot ↔ Keelathattaparai parcel is ~4-7 km road distance
        assert 1.0 < res["distance_km"] < 20.0

    def test_haversine_math_correct(self, engine_no_aws):
        """Verify haversine helper against a known pair."""
        # Delhi (28.6139°N, 77.2090°E) ↔ Mumbai (19.0760°N, 72.8777°E) ≈ 1153 km
        d = AmazonLocationServiceEngine._haversine_km(28.6139, 77.2090, 19.0760, 72.8777)
        assert 1140 < d < 1170, f"Expected ~1153 km, got {d}"


# ---------------------------------------------------------------------------
# 5) Route Calculation – AWS path
# ---------------------------------------------------------------------------

class TestRouteAWS:
    def test_uses_api_when_available(self, engine_with_mock_aws):
        engine_with_mock_aws.client.calculate_route.return_value = {
            "Summary": {"Distance": 5.4, "DurationSeconds": 720},
            "Legs": [{
                "Geometry": {
                    "LineString": [
                        [77.992, 8.752], [77.995, 8.755], [78.001, 8.760]
                    ]
                }
            }]
        }
        res = engine_with_mock_aws.calculate_agri_route("384")
        assert "Amazon Location Service" in res["source"]
        assert res["aws_credentials_available"] is True
        assert res["distance_km"] == 5.4
        assert len(res["geojson_route"]["coordinates"]) == 3  # real polyline


# ---------------------------------------------------------------------------
# 6) Geofence Audit – always local
# ---------------------------------------------------------------------------

class TestGeofenceAudit:
    def test_source_is_shapely_not_amazon(self, engine_no_aws):
        res = engine_no_aws.evaluate_cadastral_geofence("384")
        assert "GeoPandas_Shapely_UTM44N" in res["service_provider"]
        assert "Amazon Location" not in res["service_provider"]

    def test_source_is_shapely_even_with_aws(self, engine_with_mock_aws):
        """Geofence audit must ALWAYS attribute to local SpatialEngine."""
        res = engine_with_mock_aws.evaluate_cadastral_geofence("384")
        assert "GeoPandas_Shapely_UTM44N" in res["service_provider"]
        assert "Amazon Location" not in res["service_provider"]

    def test_note_explains_local(self, engine_no_aws):
        res = engine_no_aws.evaluate_cadastral_geofence("384")
        assert "does not call Amazon" in res.get("note", "")

    def test_compliant_parcel(self, engine_no_aws):
        res = engine_no_aws.evaluate_cadastral_geofence("384")
        assert res["geofence_status"] == "COMPLIANT"
        assert res["environmental_clearance"] is True

    def test_buffer_threshold_is_50m(self, engine_no_aws):
        res = engine_no_aws.evaluate_cadastral_geofence("384")
        assert res["buffer_threshold_meters"] == 50.0


# ---------------------------------------------------------------------------
# 7) configure_aws
# ---------------------------------------------------------------------------

class TestConfigureAWS:
    def test_configure_sets_env_and_returns_status(self):
        with patch.dict(os.environ, {}, clear=False):
            eng = AmazonLocationServiceEngine.__new__(AmazonLocationServiceEngine)
            from farmsync.spatial.engine import SpatialEngine
            eng.spatial = SpatialEngine()
            eng.region = "ap-south-1"
            eng.place_index = "test"
            eng.route_calculator = "test"
            eng.geofence_collection = "test"
            eng.DEFAULT_DEPOT = AmazonLocationServiceEngine.__init__.__code__ and {
                "name": "Test", "latitude": 0.0, "longitude": 0.0, "district": "Test"
            }
            eng.client = None
            # Without real AWS, client stays None, but env vars should be set
            status = eng.configure_aws("AKID", "SECRET", session_token="TOK")
            assert os.environ.get("AWS_ACCESS_KEY_ID") == "AKID"
            assert os.environ.get("AWS_SECRET_ACCESS_KEY") == "SECRET"
            assert os.environ.get("AWS_SESSION_TOKEN") == "TOK"
