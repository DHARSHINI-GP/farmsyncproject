from typing import Dict, Any, List, Optional

class EvidenceGraphBuilder:
    """
    Constructs an in-memory Directed Acyclic Graph (DAG) representing provenance
    and claim-to-source traceability for FARMSYNC.
    Outputs structured VerifiedResultObject JSON.
    """
    def build_evidence_object(
        self,
        survey_no: str,
        village: str,
        parcel_gis: Optional[Dict[str, Any]],
        doc_claims: Optional[Dict[str, Any]],
        registry_check: Optional[Dict[str, Any]],
        spatial_constraints: Optional[Dict[str, Any]],
        vision_result: Optional[Dict[str, Any]],
        advisory_result: Optional[Dict[str, Any]],
        trust_result: Optional[Dict[str, Any]],
        telemetry: Optional[Dict[str, Any]],
        agri_logistics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Builds complete VerifiedResultObject following the schema promised in the proposal.
        Safely handles missing documents, ungrounded parcels, or failed validations.
        """
        parcel_gis = parcel_gis or {}
        doc_claims = doc_claims or {}
        registry_check = registry_check or {}
        spatial_constraints = spatial_constraints or {}
        vision_result = vision_result or {}
        advisory_result = advisory_result or {}
        trust_result = trust_result or {}
        telemetry = telemetry or {}

        claim_id = f"CLM-2026-THOOTHU-{survey_no}"
        doc_found = doc_claims.get("found", False)
        
        # Build DAG Nodes and Edges for provenance visualization
        doc_label = f"Doc: {doc_claims.get('document_source', 'None')}" if doc_found else f"Doc: ABSENT ({doc_claims.get('document_source', 'None')})"
        reg_owner = registry_check.get('official_owner') or (doc_claims.get('extracted_owner') if doc_found else "UNVERIFIED")

        nodes = [
            {"id": "claim_root", "label": f"Survey {survey_no} Claim", "type": "ROOT"},
            {"id": "doc_node", "label": doc_label, "type": "EVIDENCE_DOC" if doc_found else "EVIDENCE_MISSING"},
            {"id": "db_node", "label": f"Registry: {reg_owner}", "type": "EVIDENCE_DB"},
            {"id": "gis_node", "label": f"GIS (Shapely): {parcel_gis.get('area_acres', 'N/A')} ac", "type": "DETERMINISTIC_GIS" if parcel_gis else "GIS_MISSING"},
            {"id": "photo_node", "label": f"Photo: {vision_result.get('image_filename', 'Field.jpg')}", "type": "EVIDENCE_PHOTO"},
            {"id": "crop_node", "label": f"Crop: {vision_result.get('final_verified_crop')} ({vision_result.get('final_verified_stage')})", "type": "PERCEPTION"},
            {"id": "adv_node", "label": f"Advisory: {advisory_result.get('advisory_title')}", "type": "KNOWLEDGE_RAG"},
            {"id": "trust_node", "label": f"Trust Score: {trust_result.get('fts_score')} [{trust_result.get('decision')}]", "type": "TRUST_DECISION"}
        ]
        
        edges = [
            {"from": "claim_root", "to": "doc_node", "relation": "extracted_from" if doc_found else "missing_in"},
            {"from": "claim_root", "to": "db_node", "relation": "matched_registry"},
            {"from": "claim_root", "to": "gis_node", "relation": "polygon_verified" if parcel_gis else "geometry_absent"},
            {"from": "claim_root", "to": "photo_node", "relation": "associated_field_image"},
            {"from": "photo_node", "to": "crop_node", "relation": "classified_as"},
            {"from": "crop_node", "to": "adv_node", "relation": "recommended_management"},
            {"from": "claim_root", "to": "trust_node", "relation": "evaluated_by"}
        ]

        if agri_logistics and "distance_km" in agri_logistics:
            d_km = agri_logistics.get("distance_km")
            is_aws = agri_logistics.get("aws_credentials_available", False)
            src_lbl = "Amazon Location" if is_aws else "Local Haversine"
            nodes.append({
                "id": "logistics_node",
                "label": f"Transit: {d_km} km ({src_lbl})",
                "type": "LOGISTICS_ROUTE"
            })
            edges.append({
                "from": "claim_root",
                "to": "logistics_node",
                "relation": "depot_transit_routed"
            })

        source_evidence = [
            {
                "source_type": "DOCUMENT_OCR",
                "source_ref": doc_claims.get("document_source"),
                "extracted_value": doc_claims.get("extracted_owner"),
                "claimed_extent_acres": doc_claims.get("claimed_extent_acres"),
                "page_number": doc_claims.get("page_number"),
                "confidence": doc_claims.get("ocr_confidence") if doc_found else 0.0,
                "status": "VERIFIED_EXTRACTED" if doc_found else "EVIDENCE_NOT_FOUND"
            },
            {
                "source_type": "DATABASE_REGISTRY",
                "source_ref": "Thoothukudi_Land_Registry.parcels",
                "extracted_value": reg_owner,
                "confidence": 1.00 if registry_check.get("registry_found") else 0.0,
                "status": "FOUND_IN_REGISTRY" if registry_check.get("registry_found") else "REGISTRY_ABSENT"
            },
            {
                "source_type": "FIELD_PHOTOGRAPH",
                "source_ref": vision_result.get("image_filename"),
                "extracted_crop": vision_result.get("final_verified_crop"),
                "confidence": vision_result.get("final_confidence")
            }
        ]

        if agri_logistics and "distance_km" in agri_logistics:
            source_evidence.append({
                "source_type": "AGRI_LOGISTICS_ROUTING",
                "source_ref": agri_logistics.get("source"),
                "distance_km": agri_logistics.get("distance_km"),
                "duration_minutes": agri_logistics.get("duration_minutes"),
                "aws_connected": agri_logistics.get("aws_credentials_available", False)
            })

        verified_object = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "VerifiedResultObject",
            "claim_id": claim_id,
            "survey_number": str(survey_no),
            "village": village,
            "district": parcel_gis.get("district", "Thoothukudi"),
            "extracted_attributes": {
                "registered_owner": reg_owner,
                "document_owner": doc_claims.get("extracted_owner"),
                "gis_area_acres": parcel_gis.get("area_acres"),
                "documented_area_acres": doc_claims.get("claimed_extent_acres"),
                "extent_difference_pct": registry_check.get("extent_diff_pct"),
                "predicted_crop": vision_result.get("final_verified_crop"),
                "growth_stage": vision_result.get("final_verified_stage"),
                "land_classification": doc_claims.get("land_classification") or registry_check.get("land_classification", "Agricultural"),
                "document_found": doc_found,
                "document_source": doc_claims.get("document_source")
            },
            "source_evidence": source_evidence,
            "deterministic_spatial_checks": {
                "spatial_engine": spatial_constraints.get("spatial_engine", "GeoPandas_Shapely_UTM44N"),
                "cadastral_containment_valid": spatial_constraints.get("cadastral_containment_valid", False),
                "geometry_valid": spatial_constraints.get("geometry_valid", False),
                "shapely_containment_valid": spatial_constraints.get("cadastral_containment_valid", False),
                "extent_mismatch_pct": registry_check.get("extent_diff_pct"),
                "distance_to_waterbody_meters": spatial_constraints.get("distance_to_waterbody_meters"),
                "waterbody_buffer_threshold_meters": spatial_constraints.get("waterbody_buffer_threshold_meters", 50.0),
                "waterbody_buffer_conflict": spatial_constraints.get("waterbody_buffer_conflict", False),
                "waterbody_buffer_50m_compliant": spatial_constraints.get("waterbody_buffer_50m_compliant", True),
                "distance_to_road_meters": spatial_constraints.get("distance_to_road_meters"),
                "road_accessible": spatial_constraints.get("road_accessible", True),
                "deterministic_spatial_verified": spatial_constraints.get("deterministic_spatial_verified", False)
            },
            "trust_metrics": {
                "model_reported_confidence": vision_result.get("confidence"),
                "task_trust_score_fts": trust_result.get("fts_score"),
                "verification_status": f"VERIFIED_{trust_result.get('decision')}",
                "decision_message": trust_result.get("decision_message"),
                "signal_breakdown": trust_result.get("breakdown")
            },
            "routing_telemetry": telemetry,
            "advisory_recommendation": advisory_result,
            "agri_logistics": agri_logistics,
            "evidence_graph_dag": {
                "nodes": nodes,
                "edges": edges
            }
        }
        return verified_object
