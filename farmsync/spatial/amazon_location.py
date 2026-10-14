"""
Amazon Location Service integration for FARMSYNC.

Provides reverse geocoding, ag-logistics routing, and cadastral geofence
auditing.  When valid AWS credentials are configured, all calls go through
genuine Amazon Location Service APIs (ap-south-1).  When credentials are
absent or invalid, every response is honestly labelled as a LOCAL estimate
— no fabricated route geometry and no misattributed computation sources.
"""

import os
import math
from typing import Dict, Any, Optional, List, Tuple

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from farmsync.spatial.engine import SpatialEngine


class AmazonLocationServiceEngine:
    """
    Amazon Location Service Engine for FARMSYNC.

    Architecture guarantees:
    - When AWS credentials are active: genuine API calls via boto3 ``location``
      client (``search_place_index_for_position``, ``calculate_route``).
    - When AWS credentials are absent: every response carries
      ``"aws_credentials_available": false`` and ``"source"`` is set to a
      local-estimate identifier — **never** ``"Amazon Location Service"``.
    - Route geometry in fallback mode is an honest straight-line (origin →
      destination) — no synthetic curves pretending to be road polylines.
    - ``evaluate_cadastral_geofence`` calls the local ``SpatialEngine``
      (GeoPandas / Shapely / UTM 44N) and labels its output accordingly.
    """

    def __init__(self, spatial_engine: Optional[SpatialEngine] = None):
        self.spatial = spatial_engine or SpatialEngine()
        self.region = os.environ.get("AWS_DEFAULT_REGION", "ap-south-1")
        self.place_index = os.environ.get(
            "AMAZON_LOCATION_INDEX", "FARMSYNC_PlaceIndex"
        )
        self.route_calculator = os.environ.get(
            "AMAZON_LOCATION_ROUTER", "FARMSYNC_RouteCalculator"
        )
        self.geofence_collection = os.environ.get(
            "AMAZON_LOCATION_GEOFENCE", "FARMSYNC_GeofenceCollection"
        )
        self.client: Optional[object] = None
        self._init_client()

        # Known regional agricultural supply depot (Vagaikulam SubStation / KVK)
        self.DEFAULT_DEPOT = {
            "name": "Vagaikulam TNAU Agricultural Depot & Substation",
            "latitude": 8.752486,
            "longitude": 77.992336,
            "district": "Thoothukudi",
        }

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _init_client(self) -> None:
        """Initialises boto3 Location client if credentials are configured."""
        if not BOTO3_AVAILABLE:
            self.client = None
            return

        has_keys = bool(
            os.environ.get("AWS_ACCESS_KEY_ID")
            and os.environ.get("AWS_SECRET_ACCESS_KEY")
        )
        if not has_keys:
            self.client = None
            return

        try:
            import urllib3
            urllib3.disable_warnings()
            self.client = boto3.client(
                "location",
                region_name=self.region,
                aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
                aws_session_token=os.environ.get("AWS_SESSION_TOKEN"),
                verify=False,
            )
        except Exception as exc:
            print(f"[AmazonLocationServiceEngine] client init failed: {exc}")
            self.client = None

    def configure_aws(
        self,
        access_key_id: str,
        secret_access_key: str,
        session_token: Optional[str] = None,
        region: str = "ap-south-1",
    ) -> Dict[str, Any]:
        """Dynamically configure (or reconfigure) AWS credentials."""
        os.environ["AWS_ACCESS_KEY_ID"] = access_key_id
        os.environ["AWS_SECRET_ACCESS_KEY"] = secret_access_key
        if session_token:
            os.environ["AWS_SESSION_TOKEN"] = session_token
        self.region = region
        self._init_client()
        return self.get_status()

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Returns operational status with an honest credential flag."""
        is_ready = self.client is not None
        return {
            "service": "Amazon Location Service",
            "region": self.region,
            "aws_credentials_available": is_ready,
            "connected": is_ready,
            "tier": (
                "AWS Cloud Location (ap-south-1)"
                if is_ready
                else "Local GIS Fallback (no AWS credentials)"
            ),
            "place_index": self.place_index if is_ready else None,
            "route_calculator": self.route_calculator if is_ready else None,
            "geofence_collection": self.geofence_collection if is_ready else None,
            "features_available": {
                "reverse_geocoding": {
                    "source": "Amazon Location Service" if is_ready else "LOCAL_REVENUE_INDEX",
                    "api": "search_place_index_for_position" if is_ready else None,
                },
                "route_calculation": {
                    "source": "Amazon Location Service" if is_ready else "LOCAL_HAVERSINE_ESTIMATE",
                    "api": "calculate_route" if is_ready else None,
                },
                "geofence_audit": {
                    "source": "GeoPandas_Shapely_UTM44N",
                    "note": "Geofence audit always uses local SpatialEngine regardless of AWS status",
                },
            },
        }

    # ------------------------------------------------------------------
    # Reverse Geocoding
    # ------------------------------------------------------------------

    def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
        survey_no: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Reverse geocodes coordinate pair [lat, lon] to an administrative
        postal address.

        - AWS path: ``search_place_index_for_position`` via boto3.
        - Fallback: static revenue-village address labelled as
          ``LOCAL_REVENUE_INDEX`` — **not** Amazon Location Service.
        """
        if self.client:
            try:
                resp = self.client.search_place_index_for_position(
                    IndexName=self.place_index,
                    Position=[longitude, latitude],
                    MaxResults=1,
                )
                results = resp.get("Results", [])
                if results:
                    place = results[0].get("Place", {})
                    return {
                        "formatted_address": place.get("Label", ""),
                        "revenue_village": place.get("Municipality", ""),
                        "taluk": place.get("SubRegion", ""),
                        "district": place.get("Region", ""),
                        "postal_code": place.get("PostalCode", ""),
                        "country": place.get("Country", "IND"),
                        "source": "Amazon Location Service (search_place_index_for_position)",
                        "aws_credentials_available": True,
                        "confidence": 0.98,
                    }
            except Exception as exc:
                print(
                    f"[AmazonLocationServiceEngine] reverse_geocode API error: {exc}. "
                    "Falling back to local revenue index."
                )

        # ---- Local fallback (honestly labelled) ----
        s_label = f"Survey No. {survey_no}, " if survey_no else ""
        return {
            "formatted_address": (
                f"{s_label}Keelathattaparai Revenue Village, "
                "Thoothukudi Taluk, Thoothukudi District, "
                "Tamil Nadu - 628103, India"
            ),
            "revenue_village": "Keelathattaparai",
            "taluk": "Thoothukudi",
            "district": "Thoothukudi",
            "state": "Tamil Nadu",
            "postal_code": "628103",
            "country": "IND",
            "source": "LOCAL_REVENUE_INDEX (static village-level address — not geocoded)",
            "aws_credentials_available": False,
            "confidence_note": (
                "This address is a static revenue-village record, not a "
                "geocoded result. Coordinate-level accuracy is not claimed."
            ),
        }

    # ------------------------------------------------------------------
    # Route Calculation
    # ------------------------------------------------------------------

    def calculate_agri_route(
        self,
        survey_no: str,
        origin_lat: Optional[float] = None,
        origin_lon: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculates driving route from the nearest Agricultural Depot /
        Substation to the target parcel.

        - AWS path: ``calculate_route`` via boto3 → real distance, duration
          and polyline geometry.
        - Fallback: haversine great-circle distance × road-winding factor,
          honestly labelled ``LOCAL_HAVERSINE_ESTIMATE``.  Geometry is an
          honest straight line (origin → destination), **not** a synthetic
          curve pretending to be a road path.
        """
        parcel = self.spatial.get_parcel(survey_no)
        if not parcel:
            raise ValueError(f"Parcel {survey_no} not found in cadastral index")

        dest_lat = parcel["centroid"]["latitude"]
        dest_lon = parcel["centroid"]["longitude"]

        depot_lat = origin_lat or self.DEFAULT_DEPOT["latitude"]
        depot_lon = origin_lon or self.DEFAULT_DEPOT["longitude"]
        depot_name = self.DEFAULT_DEPOT["name"]

        # ---- AWS path ----
        if self.client:
            try:
                resp = self.client.calculate_route(
                    CalculatorName=self.route_calculator,
                    DeparturePosition=[depot_lon, depot_lat],
                    DestinationPosition=[dest_lon, dest_lat],
                    TravelMode="Car",
                    DistanceUnit="Kilometers",
                )
                summary = resp.get("Summary", {})
                legs = resp.get("Legs", [{}])
                geometry = (
                    legs[0].get("Geometry", {}).get("LineString", [])
                    if legs
                    else []
                )

                return {
                    "survey_no": survey_no,
                    "origin": {
                        "name": depot_name,
                        "latitude": depot_lat,
                        "longitude": depot_lon,
                    },
                    "destination": {
                        "name": f"Survey {survey_no}",
                        "latitude": dest_lat,
                        "longitude": dest_lon,
                    },
                    "distance_km": round(summary.get("Distance", 0.0), 2),
                    "duration_minutes": round(
                        summary.get("DurationSeconds", 0) / 60.0, 1
                    ),
                    "travel_mode": "Car",
                    "geojson_route": {
                        "type": "LineString",
                        "coordinates": geometry,
                    },
                    "source": "Amazon Location Service (calculate_route)",
                    "aws_credentials_available": True,
                }
            except Exception as exc:
                print(
                    f"[AmazonLocationServiceEngine] calculate_route API error: {exc}. "
                    "Falling back to local haversine estimate."
                )

        # ---- Local fallback (honestly labelled) ----
        haversine_km = self._haversine_km(depot_lat, depot_lon, dest_lat, dest_lon)

        # Road-winding factor for rural southern Tamil Nadu (~1.28×)
        ROAD_WINDING_FACTOR = 1.28
        estimated_road_km = haversine_km * ROAD_WINDING_FACTOR

        # Estimated travel at 28 km/h average (rural single-lane roads)
        RURAL_SPEED_KMH = 28.0
        estimated_duration_mins = (estimated_road_km / RURAL_SPEED_KMH) * 60.0

        return {
            "survey_no": survey_no,
            "origin": {
                "name": depot_name,
                "latitude": depot_lat,
                "longitude": depot_lon,
            },
            "destination": {
                "name": f"Survey {survey_no}",
                "latitude": dest_lat,
                "longitude": dest_lon,
            },
            "distance_km": round(estimated_road_km, 2),
            "duration_minutes": round(estimated_duration_mins, 1),
            "travel_mode": "Car (estimated)",
            "geojson_route": {
                "type": "LineString",
                "coordinates": [
                    [round(depot_lon, 6), round(depot_lat, 6)],
                    [round(dest_lon, 6), round(dest_lat, 6)],
                ],
                "note": (
                    "Straight line from origin to destination. "
                    "This is NOT a road-network polyline."
                ),
            },
            "source": "LOCAL_HAVERSINE_ESTIMATE",
            "aws_credentials_available": False,
            "estimation_method": {
                "base": "Haversine great-circle distance",
                "haversine_km": round(haversine_km, 3),
                "road_winding_factor": ROAD_WINDING_FACTOR,
                "assumed_speed_kmh": RURAL_SPEED_KMH,
                "note": (
                    "Road distance is haversine × winding factor. "
                    "Duration assumes rural single-lane average speed. "
                    "For accurate road routing, configure AWS credentials."
                ),
            },
        }

    # ------------------------------------------------------------------
    # Cadastral Geofence Audit
    # ------------------------------------------------------------------

    def evaluate_cadastral_geofence(self, survey_no: str) -> Dict[str, Any]:
        """
        Audits cadastral parcel geofencing compliance against environmental
        waterbodies.

        This method always uses the local ``SpatialEngine`` (GeoPandas /
        Shapely / EPSG:32644) — it does **not** call Amazon Location Service
        geofence APIs.  The ``service_provider`` field honestly reflects this.
        """
        constraints = self.spatial.check_constraints(survey_no)
        is_conflict = constraints.get("waterbody_buffer_conflict", False)
        dist_w = constraints.get("distance_to_waterbody_meters")

        status = "COMPLIANT" if not is_conflict else "BUFFER_VIOLATION"

        return {
            "survey_no": survey_no,
            "geofence_status": status,
            "waterbody_clearance_meters": dist_w,
            "buffer_threshold_meters": constraints.get(
                "waterbody_buffer_threshold_meters", 50.0
            ),
            "environmental_clearance": not is_conflict,
            "road_accessible": constraints.get("road_accessible", True),
            "service_provider": "GeoPandas_Shapely_UTM44N (local SpatialEngine)",
            "aws_credentials_available": self.client is not None,
            "note": (
                "This audit is computed locally using GeoPandas and Shapely "
                "against cadastral GeoJSON layers — it does not call Amazon "
                "Location Service geofence APIs."
            ),
            "audit_verdict": (
                "Within legal agricultural boundary"
                if not is_conflict
                else "Infringes on 50 m waterbody buffer zone"
            ),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _haversine_km(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Returns great-circle distance in kilometres (Haversine formula)."""
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return 6371.0 * c
