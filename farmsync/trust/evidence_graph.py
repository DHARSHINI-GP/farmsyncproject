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

        claim_id = f"CLM-2026-THOOTHU-{survey_no or 'UNKNOWN'}"
        doc_found = doc_claims.get("found", False)
        has_photo = bool(vision_result.get("has_image", False))
        crop_name = vision_result.get("final_verified_crop") if has_photo else None
        crop_stage = vision_result.get("final_verified_stage") if has_photo else None
        
        # Build DAG Nodes and Edges for provenance visualization
        doc_label = f"Doc: {doc_claims.get('document_source', 'None')}" if doc_found else f"Doc: ABSENT ({doc_claims.get('document_source', 'None')})"
        reg_owner = registry_check.get('official_owner')

        photo_label = f"Photo: {vision_result.get('image_filename')}" if has_photo else f"Photo: NONE on record for Survey {survey_no or 'Unspecified'}"
        crop_label = f"Crop: {crop_name} ({crop_stage})" if crop_name else "Crop: UNVERIFIED (No Field Image)"
        adv_title = advisory_result.get("advisory_title") or "No Grounded Advisory"

        db_label = f"Demo Registry (RoR): {reg_owner}" if reg_owner else f"Demo Registry (RoR): NO RECORD FOR SURVEY {survey_no or 'Unspecified'}"

        nodes = [
            {"id": "claim_root", "label": f"Survey {survey_no or 'Unspecified'} Claim", "type": "ROOT"},
            {"id": "doc_node", "label": doc_label, "type": "EVIDENCE_DOC" if doc_found else "EVIDENCE_MISSING"},
            {"id": "db_node", "label": db_label, "type": "EVIDENCE_DB" if reg_owner else "REGISTRY_ABSENT"},
            {"id": "gis_node", "label": f"GIS (Shapely): {parcel_gis.get('area_acres', 'N/A')} ac", "type": "DETERMINISTIC_GIS" if parcel_gis else "GIS_MISSING"},
            {"id": "photo_node", "label": photo_label, "type": "EVIDENCE_PHOTO" if has_photo else "PHOTO_MISSING"},
            {"id": "crop_node", "label": crop_label, "type": "PERCEPTION" if crop_name else "PERCEPTION_UNAVAILABLE"},
            {"id": "adv_node", "label": f"Advisory: {adv_title}", "type": "KNOWLEDGE_RAG" if advisory_result.get("source_grounded") else "ADVISORY_UNAVAILABLE"},
            {"id": "trust_node", "label": f"Trust Score: {trust_result.get('fts_score')} [{trust_result.get('decision')}]", "type": "TRUST_DECISION"}
        ]
        
        edges = [
            {"from": "claim_root", "to": "doc_node", "relation": "extracted_from" if doc_found else "missing_in"},
            {"from": "claim_root", "to": "db_node", "relation": "matched_registry"},
            {"from": "claim_root", "to": "gis_node", "relation": "polygon_verified" if parcel_gis else "geometry_absent"},
            {"from": "claim_root", "to": "photo_node", "relation": "associated_field_image" if has_photo else "photo_unrecorded"},
            {"from": "photo_node", "to": "crop_node", "relation": "classified_as" if has_photo else "unclassified"},
            {"from": "crop_node", "to": "adv_node", "relation": "recommended_management" if advisory_result.get("source_grounded") else "no_advisory"},
            {"from": "claim_root", "to": "trust_node", "relation": "evaluated_by"}
        ]

        if agri_logistics and "distance_km" in agri_logistics and agri_logistics.get("distance_km") is not None:
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
                "source_ref": "TamilNilam_Revenue_Record_of_Rights (Demonstration Data)",
                "extracted_value": reg_owner,
                "patta_number": registry_check.get("patta_number"),
                "source_authority": registry_check.get("source_authority", "TamilNilam Revenue Record of Rights Schema (Demonstration Fixture)"),
                "data_provenance": registry_check.get("data_provenance", "DEMONSTRATION_BENCHMARK_DATA"),
                "is_authoritative_government_record": False,
                "confidence": 1.00 if reg_owner else 0.0,
                "status": "DEMO_MATCH_NOT_OFFICIAL_VERIFICATION" if reg_owner else "REGISTRY_RECORD_ABSENT",
                "disclaimer": registry_check.get("registry_disclaimer", "Demonstration benchmark dataset; not an authoritative live government confirmation.")
            },
            {
                "source_type": "FIELD_PHOTOGRAPH",
                "parcel_location_verified": vision_result.get("photo_association_verified", False),
                "source_ref": vision_result.get("image_filename"),
                "extracted_crop": crop_name,
                "confidence": vision_result.get("final_confidence") if has_photo else 0.0,
                "perception_model": (
                    vision_result.get("teacher_model")
                    if vision_result.get("escalated_to_teacher")
                    else vision_result.get("student_model")
                ),
                "is_independent_teacher": vision_result.get("is_independent_teacher", False),
                "teacher_source": vision_result.get("teacher_source"),
                "status": "VERIFIED_PERCEIVED" if has_photo else "PHOTO_ABSENT"
            }
        ]

        if agri_logistics and "distance_km" in agri_logistics and agri_logistics.get("distance_km") is not None:
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
            "survey_number": str(survey_no) if survey_no else "UNSPECIFIED",
            "village": village,
            "district": parcel_gis.get("district", "Thoothukudi") if parcel_gis else "Thoothukudi",
            "extracted_attributes": {
                "registered_owner": reg_owner,
                "document_owner": doc_claims.get("extracted_owner"),
                "ownership_verified": bool(registry_check.get("owner_match", False) and doc_found and (reg_owner is not None) and registry_check.get("is_authoritative_government_record", False)),
                "ownership_status": registry_check.get("owner_verification_status", "NOT_EVALUATED" if not doc_found else "UNVERIFIED"),
                "demo_record_matched": bool(registry_check.get("owner_match", False) and doc_found and (reg_owner is not None)),
                "ownership_verification_verdict": "demo match—not official verification" if (registry_check.get("owner_match", False) and not registry_check.get("is_authoritative_government_record", False)) else ("OFFICIAL_VERIFIED" if registry_check.get("is_authoritative_government_record", False) else "UNVERIFIED"),
                "parcel_geometry_verified": spatial_constraints.get("geometry_valid", False) if parcel_gis else False,
                "ownership_provenance": registry_check.get("data_provenance", "DEMONSTRATION_BENCHMARK_DATA"),
                "is_authoritative_government_record": bool(registry_check.get("is_authoritative_government_record", False)),
                "patta_number": registry_check.get("patta_number"),
                "gis_area_acres": parcel_gis.get("area_acres") if parcel_gis else None,
                "documented_area_acres": doc_claims.get("claimed_extent_acres"),
                "extent_difference_pct": registry_check.get("extent_diff_pct"),
                "predicted_crop": crop_name,
                "photo_association_verified": vision_result.get("photo_association_verified", False),
                "growth_stage": crop_stage,
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
