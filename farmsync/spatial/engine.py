import os
import json
import geopandas as gpd
from shapely.geometry import shape, mapping
from typing import Dict, Any, Optional, List

class SpatialEngine:
    """
    Deterministic GIS Engine for FARMSYNC.
    Executes exact spatial algorithms (area, distance buffers, containment)
    without relying on non-deterministic LLM approximations.
    """
    def __init__(self, data_root: Optional[str] = None):
        if data_root is None:
            # Default to workspace data directory
            data_root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "FAI_Product_Challange", "TASK_2", "Geospatial_Layer")
        
        self.data_root = data_root
        self.cadastral_path = os.path.join(data_root, "Park_Cadastral_Map.geojson")
        self.water_path = os.path.join(data_root, "Basic_GIS_Layers", "Waterbodies.geojson")
        self.roads_path = os.path.join(data_root, "Basic_GIS_Layers", "Road_network.geojson")
        self.substations_path = os.path.join(data_root, "Basic_GIS_Layers", "SubStations.geojson")
        
        # Load datasets in WGS84 (EPSG:4326)
        self.gdf_parcels_wgs84 = gpd.read_file(self.cadastral_path)
        self.gdf_water_wgs84 = gpd.read_file(self.water_path)
        self.gdf_roads_wgs84 = gpd.read_file(self.roads_path)
        self.gdf_substations_wgs84 = gpd.read_file(self.substations_path)
        
        # Reproject to UTM Zone 44N (EPSG:32644) for exact metric calculations in Tamil Nadu
        self.utm_crs = "EPSG:32644"
        self.gdf_parcels_utm = self.gdf_parcels_wgs84.to_crs(self.utm_crs)
        self.gdf_water_utm = self.gdf_water_wgs84.to_crs(self.utm_crs)
        self.gdf_roads_utm = self.gdf_roads_wgs84.to_crs(self.utm_crs)
        self.gdf_substations_utm = self.gdf_substations_wgs84.to_crs(self.utm_crs)
        
        # Clean survey numbers index
        self.gdf_parcels_utm["survey_no_clean"] = self.gdf_parcels_utm["survey_no"].astype(str).str.strip()
        self.gdf_parcels_wgs84["survey_no_clean"] = self.gdf_parcels_wgs84["survey_no"].astype(str).str.strip()

        # Compute cadastral boundary convex hull in UTM for deterministic containment checks
        self.cadastral_hull_utm = self.gdf_parcels_utm.geometry.union_all().convex_hull

    def list_surveys(self) -> List[str]:
        """Returns sorted list of all unique survey numbers."""
        return sorted(list(self.gdf_parcels_wgs84["survey_no_clean"].dropna().unique()))

    def get_parcel(self, survey_no: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves parcel attributes, exact GIS area in acres, and centroid coordinates.
        """
        clean_no = str(survey_no).strip()
        matches_utm = self.gdf_parcels_utm[self.gdf_parcels_utm["survey_no_clean"] == clean_no]
        matches_wgs = self.gdf_parcels_wgs84[self.gdf_parcels_wgs84["survey_no_clean"] == clean_no]
        
        # If subdivision specified (e.g., 384/1 or 384-1), check parent survey number
        if matches_utm.empty and any(sep in clean_no for sep in ["/", "-", "_"]):
            import re
            base_no = re.split(r'[/_\-]', clean_no)[0].strip()
            matches_utm = self.gdf_parcels_utm[self.gdf_parcels_utm["survey_no_clean"] == base_no]
            matches_wgs = self.gdf_parcels_wgs84[self.gdf_parcels_wgs84["survey_no_clean"] == base_no]

        if matches_utm.empty:
            return None
        
        p_utm = matches_utm.iloc[0]
        p_wgs = matches_wgs.iloc[0]
        
        area_sqm = float(p_utm.geometry.area)
        area_acres = float(area_sqm / 4046.8564224)
        
        centroid_wgs = p_wgs.geometry.centroid
        
        return {
            "survey_no": clean_no,
            "district": p_wgs.get("dist_name", "Thoothukudi"),
            "taluk": p_wgs.get("taluk_name", "Thoothukudi"),
            "village": p_wgs.get("vil_name", "Keelathattaparai"),
            "unit_id": str(p_wgs.get("unit_id", "")),
            "block_id": str(p_wgs.get("block_id", "")),
            "area_sq_meters": round(area_sqm, 2),
            "area_acres": round(area_acres, 3),
            "centroid": {
                "latitude": round(float(centroid_wgs.y), 6),
                "longitude": round(float(centroid_wgs.x), 6)
            },
            "geometry_geojson": mapping(p_wgs.geometry)
        }

    def check_constraints(
        self,
        survey_no: str,
        water_buffer_meters: float = 50.0,
        road_buffer_meters: float = 500.0
    ) -> Dict[str, Any]:
        """
        Executes deterministic spatial checks using GeoPandas and Shapely:
        - Topological validity check (is_valid)
        - Boundary containment within cadastral envelope (contains / within)
        - Distance to nearest waterbody & 50m environmental buffer compliance (Proposal Section 4.2 & 7.2)
        - Distance to nearest road & access buffer
        - Distance to nearest electrical substation
        """
        clean_no = str(survey_no).strip()
        matches = self.gdf_parcels_utm[self.gdf_parcels_utm["survey_no_clean"] == clean_no]
        if matches.empty:
            return {
                "survey_no": clean_no,
                "error": f"Survey number {survey_no} not found in cadastral map",
                "spatial_engine": "GeoPandas_Shapely_UTM44N",
                "cadastral_containment_valid": False,
                "geometry_valid": False,
                "waterbody_buffer_conflict": False,
                "waterbody_buffer_50m_compliant": False,
                "road_accessible": False,
                "deterministic_spatial_verified": False
            }

        geom = matches.iloc[0].geometry
        geom_valid = bool(geom.is_valid)
        containment_valid = bool(geom_valid and self.cadastral_hull_utm.contains(geom.centroid))

        # Calculate minimum metric distances using projected UTM geometry (EPSG:32644)
        min_dist_water = float(self.gdf_water_utm.distance(geom).min())
        min_dist_road = float(self.gdf_roads_utm.distance(geom).min())
        min_dist_substation = float(self.gdf_substations_utm.distance(geom).min())

        # Buffer checks (50m default waterbody buffer as specified in Proposal Section 4.2 & 7.2)
        waterbody_conflict = min_dist_water < water_buffer_meters
        road_accessible = min_dist_road <= road_buffer_meters

        return {
            "survey_no": clean_no,
            "spatial_engine": "GeoPandas_Shapely_UTM44N",
            "distance_to_waterbody_meters": round(min_dist_water, 2),
            "distance_to_road_meters": round(min_dist_road, 2),
            "distance_to_substation_meters": round(min_dist_substation, 2),
            "waterbody_buffer_threshold_meters": water_buffer_meters,
            "waterbody_buffer_conflict": waterbody_conflict,
            "waterbody_buffer_50m_compliant": not waterbody_conflict,
            "road_accessible": road_accessible,
            "cadastral_containment_valid": containment_valid,
            "geometry_valid": geom_valid,
            "deterministic_spatial_verified": True
        }

    def verify_extent(self, survey_no: str, claimed_acres: float, tolerance_pct: float = 5.0) -> Dict[str, Any]:
        """
        Compares documented/claimed extent with deterministic GIS polygon extent.
        Flags discrepancies exceeding tolerance_pct (default 5%).
        """
        parcel = self.get_parcel(survey_no)
        if not parcel:
            return {"error": f"Survey number {survey_no} not found"}
        
        gis_acres = parcel["area_acres"]
        delta_acres = abs(gis_acres - claimed_acres)
        delta_pct = (delta_acres / gis_acres) * 100.0 if gis_acres > 0 else 0.0
        
        is_match = delta_pct <= tolerance_pct
        
        return {
            "survey_no": str(survey_no).strip(),
            "claimed_acres": round(claimed_acres, 3),
            "gis_acres": gis_acres,
            "difference_acres": round(delta_acres, 3),
            "discrepancy_percentage": round(delta_pct, 2),
            "discrepancy_exceeded": not is_match,
            "verification_status": "MATCH" if is_match else "DISCREPANCY_FLAGGED"
        }
