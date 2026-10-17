from typing import Dict, Any, List, Optional

class CapabilityRegistry:
    """
    Registry maintaining capability, cost, latency, failure risk, and verification gain profiles.
    Used by VerifiedUtilityRouter to solve the post-verification utility objective.
    """
    REGISTRY = {
        "GEOSPATIAL_GIS": {
            "candidates": [
                {
                    "route": "GeoPandas_Shapely_Engine",
                    "type": "DETERMINISTIC_TOOL",
                    "cost_per_call": 0.0000,
                    "typical_latency_ms": 45,
                    "quality_score": 1.00,
                    "failure_risk": 0.005,
                    "verification_gain": 0.50,
                    "rationale": "Exact geometric operations must use deterministic spatial engines; LLMs hallucinate coordinate calculations."
                },
                {
                    "route": "LLM_Spatial_Reasoning",
                    "type": "PROPRIETARY_LLM",
                    "cost_per_call": 0.0150,
                    "typical_latency_ms": 1850,
                    "quality_score": 0.72,
                    "failure_risk": 0.350,
                    "verification_gain": 0.00,
                    "rationale": "Commercial LLMs suffer from geometric hallucination and high token costs for spatial math."
                }
            ],
            "default_route": "GeoPandas_Shapely_Engine"
        },
        "DATABASE_JOIN": {
            "candidates": [
                {
                    "route": "Local_Demo_Registry",
                    "type": "DETERMINISTIC_TOOL",
                    "cost_per_call": 0.0000,
                    "typical_latency_ms": 20,
                    "quality_score": 1.00,
                    "failure_risk": 0.010,
                    "verification_gain": 0.40,
                    "rationale": "Direct primary-key lookup in registry DB guarantees zero extraction hallucination."
                },
                {
                    "route": "LLM_Schema_Query",
                    "type": "PROPRIETARY_LLM",
                    "cost_per_call": 0.0050,
                    "typical_latency_ms": 1200,
                    "quality_score": 0.85,
                    "failure_risk": 0.150,
                    "verification_gain": 0.00,
                    "rationale": "Unnecessary LLM overhead for relational primary key lookups."
                }
            ],
            "default_route": "Local_Demo_Registry"
        },
        "DOCUMENT_OCR": {
            "candidates": [
                {
                    "route": "pdfplumber_Table_OCR_Extractor",
                    "type": "SPECIALIZED_MODEL",
                    "cost_per_call": 0.0002,
                    "typical_latency_ms": 120,
                    "quality_score": 0.96,
                    "failure_risk": 0.030,
                    "verification_gain": 0.45,
                    "rationale": "High-precision PDF schedule parser and OCR extracts verifiable survey tables without hallucination."
                },
                {
                    "route": "Commercial_Document_VLM",
                    "type": "PROPRIETARY_VLM",
                    "cost_per_call": 0.0100,
                    "typical_latency_ms": 2200,
                    "quality_score": 0.92,
                    "failure_risk": 0.120,
                    "verification_gain": 0.10,
                    "rationale": "Commercial VLM is 50x more expensive with lower table extraction precision on revenue forms."
                }
            ],
            "default_route": "pdfplumber_Table_OCR_Extractor"
        },
        "VISION_STUDENT": {
            "candidates": [
                {
                    "route": "MobileNetV3-CropNet-Student",
                    "type": "OPEN_WEIGHT_MODEL",
                    "cost_per_call": 0.0004,
                    "typical_latency_ms": 85,
                    "quality_score": 0.945,
                    "failure_risk": 0.055,
                    "verification_gain": 0.20,
                    "rationale": "Open-weight student model handles routine perception economically; escalates only on uncertainty."
                },
                {
                    "route": "Bedrock-Ministral-8B-Teacher",
                    "type": "PROPRIETARY_VLM",
                    "cost_per_call": 0.0045,
                    "typical_latency_ms": 680,
                    "quality_score": 0.985,
                    "failure_risk": 0.015,
                    "verification_gain": 0.30,
                    "rationale": "Proprietary reasoning model invoked conditionally when student confidence is low or evidence conflicts."
                },
                {
                    "route": "Commercial_GPT4o_Vision",
                    "type": "COMMERCIAL_VLM",
                    "cost_per_call": 0.0150,
                    "typical_latency_ms": 1450,
                    "quality_score": 0.970,
                    "failure_risk": 0.040,
                    "verification_gain": 0.20,
                    "rationale": "Expensive proprietary frontier model with high latency and token pricing."
                }
            ],
            "default_route": "MobileNetV3-CropNet-Student"
        },
        "VERIFICATION_ESCALATION": {
            "candidates": [
                {
                    "route": "Accept_Student_Perception",
                    "type": "STUDENT_VERIFICATION_PASS",
                    "cost_per_call": 0.0000,
                    "typical_latency_ms": 1,
                    "quality_score": 0.95,
                    "failure_risk": 0.05,
                    "verification_gain": 0.00,
                    "rationale": "Student model confidence exceeds utility threshold; proprietary VLM escalation safely bypassed."
                },
                {
                    "route": "Bedrock-Ministral-8B-Teacher",
                    "type": "PROPRIETARY_VLM",
                    "cost_per_call": 0.0045,
                    "typical_latency_ms": 680,
                    "quality_score": 0.985,
                    "failure_risk": 0.015,
                    "verification_gain": 0.40,
                    "rationale": "Escalated to proprietary VLM due to low confidence score (<0.75) in student model."
                }
            ],
            "default_route": "Accept_Student_Perception"
        },
        "RAG_KNOWLEDGE": {
            "candidates": [
                {
                    "route": "Local_Corpus_Retrieval",
                    "type": "HYBRID_RAG_LLM",
                    "cost_per_call": 0.0008,
                    "typical_latency_ms": 210,
                    "quality_score": 0.96,
                    "failure_risk": 0.020,
                    "verification_gain": 0.35,
                    "rationale": "Domain-grounded RAG over approved TNAU/ICAR agronomy corpus provides cited recommendations."
                },
                {
                    "route": "Generic_ZeroShot_LLM",
                    "type": "COMMERCIAL_LLM",
                    "cost_per_call": 0.0050,
                    "typical_latency_ms": 1500,
                    "quality_score": 0.70,
                    "failure_risk": 0.250,
                    "verification_gain": 0.00,
                    "rationale": "Uncited general LLM prone to hallucinations in agricultural dosage and regional cultivation."
                }
            ],
            "default_route": "Local_Corpus_Retrieval"
        },
        "TRUST_SYNTHESIS": {
            "candidates": [
                {
                    "route": "FARMSYNC_Trust_Engine",
                    "type": "DETERMINISTIC_SYNTHESIZER",
                    "cost_per_call": 0.0000,
                    "typical_latency_ms": 15,
                    "quality_score": 1.00,
                    "failure_risk": 0.000,
                    "verification_gain": 0.50,
                    "rationale": "Computes Model-Agnostic Trust Score (FTS) from independent observable evidence signals."
                },
                {
                    "route": "LLM_Self_Assessment",
                    "type": "PROPRIETARY_LLM",
                    "cost_per_call": 0.0050,
                    "typical_latency_ms": 1100,
                    "quality_score": 0.65,
                    "failure_risk": 0.300,
                    "verification_gain": 0.00,
                    "rationale": "LLM self-reported confidence is uncalibrated and sycophantic; violates verification principles."
                }
            ],
            "default_route": "FARMSYNC_Trust_Engine"
        }
    }

    def get_spec(self, subtask_type: str) -> Dict[str, Any]:
        return self.REGISTRY.get(subtask_type, self.REGISTRY["TRUST_SYNTHESIS"])


class VerifiedUtilityRouter:
    """
    Verified-Utility Router for FARMSYNC.
    Selects model or deterministic tool for each subtask by maximizing:
    RouteScore(m, t) = alpha * E[Quality(m, t)] - beta * Cost(m) - gamma * Latency(m) - delta * Risk(m, t) + eta * Delta_VerifGain
    """
    def __init__(
        self,
        registry: Any = None,
        alpha: float = 1.0,
        beta: float = 50.0,
        gamma: float = 0.25,
        delta: float = 1.2,
        eta: float = 0.6
    ):
        if isinstance(registry, CapabilityRegistry):
            self.registry = registry
        else:
            self.registry = CapabilityRegistry()
        self.CAPABILITY_REGISTRY = self.registry.REGISTRY

        # Calibrated objective weights from Section 3.1
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.delta = delta
        self.eta = eta

    def compute_utility(
        self,
        candidate: Dict[str, Any],
        subtask_type: str,
        measured_confidence: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Computes the verified utility score for a candidate route on a specific subtask.
        Dynamically incorporates measured confidence from perception modules.
        """
        quality = candidate["quality_score"]
        risk = candidate["failure_risk"]

        # Dynamically calibrate student / pass routes when empirical confidence is available
        if measured_confidence is not None:
            if candidate["route"] in ("MobileNetV3-CropNet-Student", "Accept_Student_Perception"):
                quality = max(0.0, min(1.0, float(measured_confidence)))
                risk = max(0.0, min(1.0, 1.0 - quality))

        cost = candidate["cost_per_call"]
        latency_sec = candidate["typical_latency_ms"] / 1000.0
        verif_gain = candidate.get("verification_gain", 0.0)

        quality_term = self.alpha * quality
        cost_penalty = self.beta * cost
        latency_penalty = self.gamma * latency_sec
        risk_penalty = self.delta * risk
        verif_term = self.eta * verif_gain

        score = quality_term - cost_penalty - latency_penalty - risk_penalty + verif_term

        return {
            "route_score": round(score, 4),
            "quality_term": round(quality_term, 4),
            "cost_penalty": round(cost_penalty, 4),
            "latency_penalty": round(latency_penalty, 4),
            "risk_penalty": round(risk_penalty, 4),
            "verif_gain_term": round(verif_term, 4),
            "effective_quality": round(quality, 4),
            "effective_risk": round(risk, 4),
            "cost_usd": cost,
            "latency_ms": candidate["typical_latency_ms"]
        }

    def select_optimal_route(
        self,
        subtask_type: str,
        measured_confidence: Optional[float] = None,
        force_escalation: bool = False
    ) -> Dict[str, Any]:
        """
        Solves the verified-utility optimization problem:
        c* = argmax_{c in Candidates} RouteScore(c, t)
        """
        spec = self.registry.get_spec(subtask_type)
        candidates = spec.get("candidates", [])

        evaluated_candidates = []
        best_candidate = None
        best_utility = None
        best_score = -float("inf")

        for cand in candidates:
            utility = self.compute_utility(cand, subtask_type, measured_confidence=measured_confidence)
            score = utility["route_score"]

            # Forced escalation priority override (for manual test scenarios)
            if force_escalation:
                if "Teacher" in cand["route"]:
                    score += 10.0
                elif cand["route"] in ("MobileNetV3-CropNet-Student", "Accept_Student_Perception"):
                    score -= 10.0

            cand_eval = {
                "route": cand["route"],
                "type": cand["type"],
                "score": round(score, 4),
                "utility": utility,
                "candidate_meta": cand
            }
            evaluated_candidates.append(cand_eval)

            if score > best_score:
                best_score = score
                best_candidate = cand
                best_utility = utility

        # Safety fallback
        if not best_candidate:
            best_candidate = candidates[0] if candidates else {
                "route": spec.get("default_route", "DEFAULT"),
                "type": "TOOL",
                "typical_latency_ms": 10,
                "cost_per_call": 0.0,
                "rationale": "Default route"
            }
            best_utility = self.compute_utility(best_candidate, subtask_type, measured_confidence)

        rationale = best_candidate.get("rationale", "")
        if "Teacher" in best_candidate["route"] and (force_escalation or (measured_confidence is not None and measured_confidence < 0.75)):
            conf_str = f"confidence {measured_confidence:.2f}" if measured_confidence is not None else "manual override"
            rationale = f"Escalated to proprietary VLM due to low confidence score (<0.75) in student model ({conf_str})."

        return {
            "subtask_type": subtask_type,
            "selected_route": best_candidate["route"],
            "route_type": best_candidate["type"],
            "estimated_cost_usd": best_candidate["cost_per_call"],
            "latency_ms": best_candidate["typical_latency_ms"],
            "routing_rationale": rationale,
            "route_score": round(best_score, 4),
            "utility_breakdown": best_utility,
            "alternatives_evaluated": evaluated_candidates
        }

    def route_subtask(
        self,
        subtask_type: str,
        force_escalation: bool = False,
        measured_confidence: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Determines the optimal route by optimizing the Verified-Utility objective.
        Backward-compatible interface for orchestrator subtask execution.
        """
        return self.select_optimal_route(
            subtask_type=subtask_type,
            measured_confidence=measured_confidence,
            force_escalation=force_escalation
        )
