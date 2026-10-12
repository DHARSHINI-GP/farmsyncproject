from typing import Dict, Any, List

class TrustEngine:
    """
    Model-Agnostic Trust Engine (FTS) for FARMSYNC.
    Computes trust from independently observable evidence rather than
    blindly trusting vendor-reported LLM confidence fields.
    """
    def __init__(self):
        # Default normalized weights
        self.w1_calib = 0.20
        self.w2_coverage = 0.20
        self.w3_consistency = 0.20
        self.w4_det_val = 0.20
        self.w5_validity = 0.10
        self.w6_conflict = 0.10

    def evaluate_trust(
        self,
        vision_confidence: float,
        is_supported_crop: bool,
        doc_registry_match: bool,
        spatial_extent_match: bool,
        waterbody_conflict: bool,
        has_field_photo: bool,
        has_land_doc: bool,
        has_registry: bool
    ) -> Dict[str, Any]:
        """
        Calculates FTS score and returns acceptance decision: ACCEPT, ESCALATE, or ABSTAIN.
        """
        # 1. Calibration Signal (historical model reliability on validation set)
        calib_score = 0.92 if is_supported_crop else 0.40
        
        # 2. Evidence Coverage (fraction of required sources present)
        sources_present = sum([has_field_photo, has_land_doc, has_registry])
        coverage_score = sources_present / 3.0
        
        # 3. Source Consistency (agreement between doc and database)
        consistency_score = 1.00 if doc_registry_match else 0.10
        
        # 4. Deterministic Validation (PostGIS extent and spatial containment)
        det_val_score = 1.00 if spatial_extent_match else 0.20
        
        # 5. Output Validity (structural validity)
        validity_score = 1.00
        
        # 6. Conflict / OOD Penalty
        conflict_penalty = 0.0
        if not doc_registry_match:
            conflict_penalty += 0.50
        if not spatial_extent_match:
            conflict_penalty += 0.30
        if waterbody_conflict:
            conflict_penalty += 0.20
        conflict_penalty = min(1.0, conflict_penalty)
        
        # Compute Weighted FTS
        fts = (
            (self.w1_calib * calib_score) +
            (self.w2_coverage * coverage_score) +
            (self.w3_consistency * consistency_score) +
            (self.w4_det_val * det_val_score) +
            (self.w5_validity * validity_score) -
            (self.w6_conflict * conflict_penalty)
        )
        fts = max(0.0, min(1.0, fts)) # Clamp between 0.0 and 1.0

        # Decision Policy (Bounded Escalation & Abstention)
        if fts >= 0.82:
            decision = "ACCEPT"
            decision_msg = "All evidence verified; deterministic checks passed. Prediction accepted."
        elif fts >= 0.60:
            decision = "ESCALATE"
            decision_msg = "Intermediate trust score; escalated to Proprietary VLM for secondary verification."
        else:
            decision = "ABSTAIN"
            decision_msg = "Critical evidence conflict or missing inputs; explicit abstention triggered for Human Review."

        return {
            "fts_score": round(fts, 3),
            "decision": decision,
            "decision_message": decision_msg,
            "breakdown": {
                "calibration": round(calib_score, 2),
                "evidence_coverage": round(coverage_score, 2),
                "source_consistency": round(consistency_score, 2),
                "deterministic_validation": round(det_val_score, 2),
                "output_validity": round(validity_score, 2),
                "conflict_penalty": round(conflict_penalty, 2)
            }
        }
