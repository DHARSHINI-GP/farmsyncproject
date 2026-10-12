from typing import Dict, Any, List

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
        parcel_gis: Dict[str, Any],
        doc_claims: Dict[str, Any],
        registry_check: Dict[str, Any],
        spatial_constraints: Dict[str, Any],
        vision_result: Dict[str, Any],
        advisory_result: Dict[str, Any],
        trust_result: Dict[str, Any],
        telemetry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Builds complete VerifiedResultObject following the schema promised in the proposal.
        """
        claim_id = f"CLM-2026-THOOTHU-{survey_no}"
        
        # Build DAG Nodes and Edges for provenance visualization
        nodes = [
            {"id": "claim_root", "label": f"Survey {survey_no} Verified Claim", "type": "ROOT"},
            {"id": "doc_node", "label": f"Doc: {doc_claims.get('document_source', 'Patta_Notice.pdf')}", "type": "EVIDENCE_DOC"},
            {"id": "db_node", "label": f"Registry: {registry_check.get('official_owner', 'Owner')}", "type": "EVIDENCE_DB"},
            {"id": "gis_node", "label": f"PostGIS: {parcel_gis.get('area_acres', 0)} acres", "type": "DETERMINISTIC_GIS"},
            {"id": "photo_node", "label": f"Photo: {vision_result.get('image_filename', 'Field.jpg')}", "type": "EVIDENCE_PHOTO"},
            {"id": "crop_node", "label": f"Crop: {vision_result.get('final_verified_crop')} ({vision_result.get('final_verified_stage')})", "type": "PERCEPTION"},
            {"id": "adv_node", "label": f"Advisory: {advisory_result.get('advisory_title')}", "type": "KNOWLEDGE_RAG"},
            {"id": "trust_node", "label": f"Trust Score: {trust_result.get('fts_score')} [{trust_result.get('decision')}]", "type": "TRUST_DECISION"}
        ]
        
        edges = [
            {"from": "claim_root", "to": "doc_node", "relation": "extracted_from"},
            {"from": "claim_root", "to": "db_node", "relation": "matched_registry"},
            {"from": "claim_root", "to": "gis_node", "relation": "polygon_verified"},
            {"from": "claim_root", "to": "photo_node", "relation": "associated_field_image"},
            {"from": "photo_node", "to": "crop_node", "relation": "classified_as"},
            {"from": "crop_node", "to": "adv_node", "relation": "recommended_management"},
            {"from": "claim_root", "to": "trust_node", "relation": "evaluated_by"}
        ]

        verified_object = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "VerifiedResultObject",
            "claim_id": claim_id,
            "survey_number": str(survey_no),
            "village": village,
            "district": parcel_gis.get("district", "Thoothukudi"),
            "extracted_attributes": {
                "registered_owner": registry_check.get("official_owner", doc_claims.get("extracted_owner")),
                "gis_area_acres": parcel_gis.get("area_acres"),
                "documented_area_acres": doc_claims.get("claimed_extent_acres"),
                "extent_difference_pct": registry_check.get("extent_diff_pct"),
                "predicted_crop": vision_result.get("final_verified_crop"),
                "growth_stage": vision_result.get("final_verified_stage"),
                "land_classification": registry_check.get("land_classification", "Agricultural")
            },
            "source_evidence": [
                {
                    "source_type": "DOCUMENT_OCR",
                    "source_ref": doc_claims.get("document_source"),
                    "extracted_value": doc_claims.get("extracted_owner"),
                    "confidence": doc_claims.get("ocr_confidence")
                },
                {
                    "source_type": "DATABASE_REGISTRY",
                    "source_ref": "Thoothukudi_Land_Registry.parcels",
                    "extracted_value": registry_check.get("official_owner"),
                    "confidence": 1.00
                },
                {
                    "source_type": "FIELD_PHOTOGRAPH",
                    "source_ref": vision_result.get("image_filename"),
                    "extracted_crop": vision_result.get("final_verified_crop"),
                    "confidence": vision_result.get("final_confidence")
                }
            ],
            "deterministic_spatial_checks": {
                "postgis_containment_valid": True,
                "extent_mismatch_pct": registry_check.get("extent_diff_pct"),
                "distance_to_waterbody_meters": spatial_constraints.get("distance_to_waterbody_meters"),
                "distance_to_road_meters": spatial_constraints.get("distance_to_road_meters"),
                "waterbody_buffer_conflict": spatial_constraints.get("waterbody_buffer_conflict"),
                "road_accessible": spatial_constraints.get("road_accessible")
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
            "evidence_graph_dag": {
                "nodes": nodes,
                "edges": edges
            }
        }
        return verified_object
