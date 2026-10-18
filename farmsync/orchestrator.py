import os
import time
from typing import Dict, Any, Optional, List, Set

from farmsync.router.compiler import TaskGraphCompiler, TaskGraph, TaskNode
from farmsync.router.router import CapabilityRegistry, VerifiedUtilityRouter
from farmsync.documents.extractor import DocumentRegistryEngine
from farmsync.spatial.engine import SpatialEngine
from farmsync.spatial.amazon_location import AmazonLocationServiceEngine
from farmsync.vision.classifier import CropVisionClassifier
from farmsync.knowledge.advisory import AgronomyKnowledgeEngine
from farmsync.trust.trust_score import TrustEngine
from farmsync.trust.evidence_graph import EvidenceGraphBuilder


class FarmSyncOrchestrator:
    """
    Core Production AI Orchestrator for FARMSYNC.
    Coordinates end-to-end multimodal geospatial execution by executing compiled DAGs:
    1. Query deconstruction into a typed executable TaskGraph DAG
    2. Topological execution loop verifying prerequisite node dependencies
    3. Mathematical Verified-Utility routing for every subtask node
    4. Real PDF document table & OCR parsing
    5. Cadastral registry cross-checking
    6. Deterministic GeoPandas/Shapely spatial calculations & buffer checks
    7. Field photo perception with PyTorch student model inference
    8. Dynamic teacher VLM escalation based on measured confidence
    9. Grounded TNAU/ICAR agronomy knowledge retrieval
    10. In-memory evidence graph DAG construction
    11. Model-Agnostic Trust Score (FTS) evaluation & bounded abstention
    """
    def __init__(self, data_root: Optional[str] = None):
        print("Initializing FARMSYNC Production Orchestrator...")
        self.compiler = TaskGraphCompiler()
        self.registry = CapabilityRegistry()
        self.router = VerifiedUtilityRouter(self.registry)

        # Grounded tool connectors
        self.docs = DocumentRegistryEngine()
        self.spatial = SpatialEngine(data_root=data_root)
        self.location_engine = AmazonLocationServiceEngine(spatial_engine=self.spatial)
        self.vision = CropVisionClassifier()
        self.knowledge = AgronomyKnowledgeEngine()

        # Trust & Verification
        self.trust_engine = TrustEngine()
        self.graph_builder = EvidenceGraphBuilder()

        # Empirical 50-Query Benchmark Results
        self.benchmark_results_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "benchmark_results.json"
        )

    def _load_benchmark_summary(self):
        """Historical results do not validate the current implementation."""
        return {'status': 'NOT_CURRENTLY_VALIDATED', 'verified_accuracy_pct': None,
                'actual_cost_savings_pct': None, 'reason': 'Requires a new independently reviewed evaluation'}

    def execute_request(
        self,
        query: str,
        document_path: Optional[str] = None,
        survey_no: Optional[str] = None,
        force_escalate_vision: bool = False,
        simulate_conflict: bool = False,
        simulate_unsupported_crop: bool = False,
        parcel_id: Optional[str] = None,
        image_filename: Optional[str] = None,
        event_callback=None,
        cancel_check=None
    ) -> Dict[str, Any]:
        """
        Executes an end-to-end multimodal geospatial request by walking the compiled TaskGraph DAG
        in topological order, resolving dependencies, optimizing route utility, and recording runtime states.
        """
        start_time = time.time()

        # Step 1: Compile query into executable TaskGraph DAG
        from farmsync.router.planner import DomainPlanner
        plan = DomainPlanner().plan(query, has_document=bool(document_path), has_image=bool(image_filename))
        task_graph: TaskGraph = self.compiler.compile(query, plan=plan)
        target_survey = survey_no or task_graph.target_survey_no
        # Resolve village: prefer planner result, then revenue registry, then spatial parcel
        village = task_graph.target_village
        if not village and target_survey:
            reg_entry = self.docs.revenue_registry.get(str(target_survey), {})
            village = reg_entry.get("village") or "Keelathattaparai"
        village = village or "Keelathattaparai"
        selected = self.spatial.get_parcel(parcel_id) if parcel_id else None
        if selected and selected["survey_no"] == str(target_survey):
            parcel_key = parcel_id
            village = selected["village"]
        else:
            parcel_key = target_survey

        target_doc = document_path or task_graph.target_document

        # Step 2: Shared execution context for passing data between DAG nodes
        context: Dict[str, Any] = {
            "query": query,
            "survey_no": target_survey,
            "parcel_key": parcel_key,
            "image_filename": image_filename,
            "village": village,
            "document_path": target_doc,
            "workflow_type": task_graph.workflow_type,
            "water_buffer_meters": self.compiler.extract_buffer_distance(query),
            "force_escalate_vision": force_escalate_vision,
            "simulate_conflict": simulate_conflict,
            "simulate_unsupported_crop": simulate_unsupported_crop,
            "doc_claims": None,
            "reg_check": None,
            "parcel_gis": None,
            "spatial_constraints": None,
            "extent_check": None,
            "img_record": None,
            "vision_result": None,
            "vision_confidence": None,
            "final_crop": None,
            "final_stage": None,
            "advisory_result": None,
            "agri_logistics": None,
            "trust_result": None
        }

        # Step 3: Topologically execute DAG nodes
        execution_order: List[TaskNode] = task_graph.topological_sort()
        completed_tasks: Set[str] = set()
        telemetry_steps: List[Dict[str, Any]] = []
        total_cost = 0.0

        for task in execution_order:
            if cancel_check:
                cancel_check()
            # Enforce dependency resolution
            if not task_graph.are_deps_satisfied(task.id, completed_tasks):
                unmet = [d for d in task.deps if d not in completed_tasks]
                task.mark_failed(f"Unmet dependencies: {unmet}")
                continue

            task.mark_running()
            if event_callback:
                event_callback({"task_id": task.id, "name": task.name, "status": "RUNNING"})
            node_start = time.time()

            # Step 3a: Mathematical Verified-Utility Route Selection
            measured_conf = context.get("vision_confidence")
            is_esc_task = task.subtask_type in ("VISION_STUDENT", "VERIFICATION_ESCALATION")
            route_decision = self.router.select_optimal_route(
                subtask_type=task.subtask_type,
                measured_confidence=measured_conf if is_esc_task else None,
                force_escalation=force_escalate_vision if is_esc_task else False
            )

            # Step 3b: Execute specific task logic
            step_meta = self._execute_task_node(task, context, route_decision)

            node_elapsed_ms = int((time.time() - node_start) * 1000)
            step_latency = node_elapsed_ms
            cost = route_decision["estimated_cost_usd"]
            if task.subtask_type in ("VISION_STUDENT", "VERIFICATION_ESCALATION") and not (context.get("vision_result") or {}).get("has_image"):
                cost = 0.0
            total_cost += cost

            task.mark_completed(
                result=step_meta,
                cost_usd=cost,
                latency_ms=step_latency,
                route_decision=route_decision
            )
            completed_tasks.add(task.id)
            if event_callback:
                event_callback({"task_id": task.id, "name": task.name, "status": "COMPLETED", "latency_ms": node_elapsed_ms, "actual_execution_model": step_meta.get("actual_execution_model")})

            # Step 3c: Append to execution telemetry
            step_record = {
                "task_id": task.id,
                "name": task.name,
                "model_or_tool": route_decision["selected_route"],
                "type": route_decision["route_type"],
                "latency_ms": step_latency,
                "cost_usd": cost,
                "route_score": route_decision["route_score"],
                "rationale": route_decision["routing_rationale"],
                "status": task.status
            }
            step_record.update(step_meta)
            step_record["planned_route"] = route_decision["selected_route"]
            step_record["estimated_latency_ms"] = route_decision["latency_ms"]
            step_record["model_or_tool"] = step_meta.get("actual_execution_model") or route_decision["selected_route"]
            telemetry_steps.append(step_record)

        total_latency_ms = int((time.time() - start_time) * 1000)

        # Step 4: Build Telemetry Summary
        has_escalated = any(
            step.get("escalation_decision") == "ESCALATED_TO_TEACHER" or 
            "Teacher" in str(step.get("model_or_tool", "")) or
            "Teacher" in str(step.get("actual_execution_model", ""))
            for step in telemetry_steps
        )
        telemetry_summary = {
            "planner_source": getattr(task_graph, "planner_source", "VALIDATED_DOMAIN_TEMPLATE"),
            "planning_usage": getattr(task_graph, "planning_usage", {}),
            "plan_fallback": bool(plan and plan.get("fallback")),
            "total_latency_ms": total_latency_ms,
            "total_estimated_cost_usd": round(total_cost, 5),
            "step_count": len(telemetry_steps),
            "escalated_to_teacher": has_escalated,
            "steps": telemetry_steps
        }

        # Step 5: Construct Evidence Graph DAG and VerifiedResultObject
        doc_claims = context["doc_claims"] or {}
        reg_check = context["reg_check"] or {}
        parcel_gis = context["parcel_gis"]
        spatial_constraints = context["spatial_constraints"] or {}
        vision_result = context["vision_result"] or {}
        advisory_result = context["advisory_result"] or {}
        agri_logistics = context["agri_logistics"]
        trust_result = context["trust_result"] or {}
        if parcel_gis:
            village = parcel_gis["village"]

        verified_result = self.graph_builder.build_evidence_object(
            survey_no=target_survey,
            village=village,
            parcel_gis=parcel_gis,
            doc_claims=doc_claims,
            registry_check=reg_check,
            spatial_constraints=spatial_constraints,
            vision_result=vision_result,
            advisory_result=advisory_result,
            trust_result=trust_result,
            telemetry=telemetry_summary,
            agri_logistics=agri_logistics
        )
        # Document-vs-GIS extent is distinct from document-vs-demo-registry extent.
        extent_check = context["extent_check"] or {}
        extent_pct = extent_check.get("discrepancy_percentage") if doc_claims.get("found") and extent_check.get('verification_status') in {'MATCH','MISMATCH','DISCREPANCY_FLAGGED'} else None
        verified_result["extracted_attributes"]["extent_difference_pct"] = extent_pct
        verified_result["deterministic_spatial_checks"]["extent_mismatch_pct"] = extent_pct
        verified_result["deterministic_spatial_checks"]["extent_verification"] = extent_check
        verified_result["parcel_id"] = (parcel_gis or {}).get("parcel_id")
        verified_result["extracted_attributes"]["crop_matches_parcel"] = context.get("crop_matches_parcel", True)
        verified_result["extracted_attributes"]["expected_crop"] = context.get("expected_crop")
        verified_result["extracted_attributes"]["crop_mismatch_detected"] = bool(not context.get("crop_matches_parcel", True))
        
        doc_prov = bool(context.get("document_path"))
        doc_ver = reg_check.get("document_verified", False)
        doc_mis = reg_check.get("document_mismatch", False) or (doc_prov and not doc_ver)
        verified_result["extracted_attributes"]["document_provided"] = doc_prov
        verified_result["extracted_attributes"]["document_verified"] = doc_ver
        verified_result["extracted_attributes"]["document_mismatch"] = doc_mis
        verified_result["extracted_attributes"]["survey_match"] = reg_check.get("survey_match", False)
        verified_result["extracted_attributes"]["extent_match"] = reg_check.get("extent_match", False)
        verified_result["extracted_attributes"]["doc_survey_no"] = reg_check.get("doc_survey_no")
        verified_result["extracted_attributes"]["target_survey_no"] = target_survey
        verified_result["extracted_attributes"]["document_extent_acres"] = reg_check.get("document_extent_acres") or doc_claims.get("claimed_extent_acres")
        verified_result["extracted_attributes"]["expected_acres"] = reg_check.get("official_extent_acres")
        verified_result["extracted_attributes"]["doc_verification_details"] = reg_check.get("details")
        verified_result["extracted_attributes"]["doc_verification_status"] = reg_check.get("verification_status", "ABSENT")

        if doc_mis:
            verified_result["extracted_attributes"]["ownership_verified"] = False
            verified_result["extracted_attributes"]["ownership_status"] = "DOCUMENT_MISMATCH_REJECT"
        elif reg_check.get("owner_match", False) and doc_claims.get("found"):
            verified_result["extracted_attributes"]["ownership_verified"] = True
            verified_result["extracted_attributes"]["ownership_status"] = "OWNERSHIP_VERIFIED_MATCH"
        verified_result["trust_metrics"]["score_kind"] = "HEURISTIC_EVIDENCE_SCORE_NOT_A_PROBABILITY"
        verified_result["trust_metrics"]["policy_version"] = "source-only-2.1"

        # Historical simulations do not establish present accuracy or actual savings.
        baseline_comparison = {
            "benchmark_suite": "Historical 50-query suite is invalid for the corrected source-evidence policy",
            "total_benchmark_queries": 0,
            "current_configuration_validated": False,
            "benchmark_notice": "Current workflow latency is measured. Routing costs are estimates. Accuracy, hallucination rates and savings require a new validated comparison.",
            "FARMSYNC": {
                "evaluation_type": "current_workflow_telemetry",
                "cost_usd": round(total_cost, 5), "latency_ms": total_latency_ms,
                "verified_accuracy_pct": None, "hallucination_rate_pct": None,
                "cost_savings_vs_premium_pct": None, "benchmark_measured_accuracy_pct": None,
            },
            "Premium_Only": {"evaluation_type": "NOT_EXECUTED", "benchmark_measured_accuracy_pct": None},
            "Static_Routing": {"evaluation_type": "NOT_EXECUTED", "benchmark_measured_accuracy_pct": None},
        }

        return {
            "query": query,
            "workflow_type": task_graph.workflow_type,
            "target_survey_no": target_survey,
            "document_source_used": doc_claims.get("document_source"),
            "document_found": doc_claims.get("found", False),
            "executed_dag": task_graph.to_dict(),
            "verified_result_object": verified_result,
            "baseline_comparison": baseline_comparison
        }

    def _execute_task_node(
        self,
        task: TaskNode,
        context: Dict[str, Any],
        route_decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executes a discrete DAG task node, writing outputs into the shared context.
        """
        stype = task.subtask_type

        if stype == "DOCUMENT_OCR":
            doc_claims = self.docs.extract_document_claims(
                doc_path=context["document_path"],
                survey_no=context["survey_no"],
                simulate_mismatch=context["simulate_conflict"]
            )
            source_village = doc_claims.get('document_village')
            if source_village and context.get('village'):
                # Only discard if BOTH the registry village AND the parcel village differ.
                # Prevents false conflicts when the query village defaults differ from the document.
                reg_village = (self.docs.revenue_registry.get(str(context.get('survey_no', '')), {}) or {}).get('village', '')
                doc_v = source_village.strip().casefold()
                ctx_v = context['village'].strip().casefold()
                reg_v = reg_village.strip().casefold()
                # Conflict only when doc village matches neither the context nor the registry
                if doc_v != ctx_v and doc_v != reg_v and reg_v and doc_v:
                    doc_claims = {**doc_claims, 'found':False, 'extracted_owner':None, 'claimed_extent_acres':None,
                                  'status':'DOCUMENT_VILLAGE_CONFLICT', 'observations':[doc_claims],
                                  'error':'The document village conflicts with the selected parcel; source claims were not applied to that parcel.'}
            context["doc_claims"] = doc_claims
            return {
                "document_source": doc_claims.get("document_source"),
                "actual_execution_model": doc_claims.get("extraction_method") or "Local PDF extractor",
                "extraction_method": doc_claims.get("extraction_method"),
                "evidence_found": doc_claims.get("found", False)
            }

        elif stype == "DATABASE_JOIN":
            reg_check = self.docs.cross_check_registry(context["doc_claims"])
            selected = self.spatial.get_parcel(context["parcel_key"])
            record = self.docs.revenue_registry.get(str(context["survey_no"]), {})
            if selected and record.get("village") and record["village"].casefold() != selected["village"].casefold():
                reg_check.update({"registry_found": False, "owner_match": False, "official_owner": None, "owner_verification_status": "VILLAGE_IDENTITY_MISMATCH"})
            context["reg_check"] = reg_check
            return {
                "actual_execution_model": "Local demonstration JSON registry",
                "registry_status": reg_check.get("status")
            }

        elif stype == "GEOSPATIAL_GIS":
            if context.get("spatial_constraints") is not None:
                return {"actual_execution_model": "Cached GeoPandas/Shapely result for this run", "cadastral_found": context.get("parcel_gis") is not None}
            target_survey = context["parcel_key"]
            doc_claims = context["doc_claims"] or {}
            parcel_gis = self.spatial.get_parcel(target_survey) if target_survey else None
            context["parcel_gis"] = parcel_gis

            if parcel_gis:
                context["village"] = parcel_gis["village"]
                spatial_constraints = self.spatial.check_constraints(target_survey, water_buffer_meters=context["water_buffer_meters"])
                claimed_ac = doc_claims.get("claimed_extent_acres")
                if claimed_ac is not None and claimed_ac > 0:
                    extent_check = self.spatial.verify_extent(target_survey, claimed_ac)
                else:
                    extent_check = {
                        "survey_no": target_survey,
                        "claimed_acres": None,
                        "gis_acres": parcel_gis["area_acres"],
                        "difference_acres": None,
                        "discrepancy_percentage": None,
                        "discrepancy_exceeded": None,
                        "verification_status": "DOCUMENT_EXTENT_NOT_AVAILABLE"
                    }
                try:
                    agri_logistics = self.location_engine.calculate_agri_route(target_survey)
                except Exception as e:
                    agri_logistics = {
                        "survey_no": target_survey,
                        "error": str(e),
                        "aws_credentials_available": False
                    }
                context["agri_logistics"] = agri_logistics
            else:
                spatial_constraints = {
                    "survey_no": target_survey or "UNSPECIFIED",
                    "error": f"Survey number '{target_survey}' not found in cadastral geospatial layer",
                    "spatial_engine": "GeoPandas_Shapely_UTM44N",
                    "cadastral_containment_valid": False,
                    "geometry_valid": False,
                    "waterbody_buffer_threshold_meters": 50.0,
                    "waterbody_buffer_conflict": False,
                    "waterbody_buffer_50m_compliant": False,
                    "road_accessible": False,
                    "deterministic_spatial_verified": False,
                    "status": "PARCEL_NOT_FOUND_IN_CADASTRAL"
                }
                extent_check = {
                    "survey_no": target_survey or "UNSPECIFIED",
                    "claimed_acres": doc_claims.get("claimed_extent_acres"),
                    "gis_acres": None,
                    "difference_acres": None,
                    "discrepancy_percentage": None,
                    "discrepancy_exceeded": None,
                    "verification_status": "CADASTRAL_PARCEL_NOT_FOUND"
                }
                context["agri_logistics"] = {
                    "survey_no": target_survey or "UNSPECIFIED",
                    "status": "NO_PARCEL_COORDINATES",
                    "error": f"Survey '{target_survey}' not found in cadastral map",
                    "aws_credentials_available": False,
                    "distance_km": None
                }

            context["spatial_constraints"] = spatial_constraints
            context["extent_check"] = extent_check
            return {
                "actual_execution_model": "GeoPandas/Shapely EPSG:32644",
                "cadastral_found": parcel_gis is not None
            }

        elif stype == "VISION_STUDENT":
            target_survey = context["survey_no"]
            parcel = self.spatial.get_parcel(context["parcel_key"])
            matched_photo = self.vision.get_image_for_survey(target_survey, parcel=parcel) if target_survey and parcel else None
            img_record = self.vision.image_registry.get(context["image_filename"]) if context.get("image_filename") else matched_photo
            photo_aligned = False
            if img_record and parcel:
                from shapely.geometry import shape, Point
                try:
                    lat, lon = float(img_record.get("latitude")), float(img_record.get("longitude"))
                    photo_aligned = shape(parcel["geometry_geojson"]).covers(Point(lon, lat))
                except (ValueError, TypeError):
                    pass
            if img_record and img_record.get("location_source"):
                # User-entered coordinates are a claim, not independently verified
                # field-photo provenance. They cannot raise parcel evidence trust.
                vision_coordinate_containment = photo_aligned
                photo_aligned = False
            else:
                vision_coordinate_containment = photo_aligned
            context["img_record"] = img_record
            img_path = img_record["filepath"] if img_record else None

            # Student neural inference (or teacher if forced by router)
            is_forced = (route_decision["selected_route"] == "Bedrock-Ministral-8B-Teacher")
            vision_result = self.vision.predict_crop(
                img_path,
                simulate_ood=context["simulate_unsupported_crop"],
                force_escalate=is_forced
            )
            predicted_crop = vision_result.get("final_verified_crop")
            
            # Check crop consistency against parcel's expected/registered crop:
            expected_crop = (
                (self.docs.revenue_registry.get(str(target_survey or ""), {}) or {}).get("expected_crop")
            )
            if not expected_crop and target_survey:
                gt_files = self.vision.survey_image_index.get(str(target_survey), [])
                if gt_files:
                    gt_crops = [self.vision.image_registry[f].get("true_crop") for f in gt_files if f in self.vision.image_registry]
                    if gt_crops:
                        expected_crop = gt_crops[0]

            crop_matches_parcel = True
            if expected_crop and predicted_crop:
                exp_norm = expected_crop.lower().split("(")[0].strip()
                pred_norm = predicted_crop.lower().split("(")[0].strip()
                if exp_norm != pred_norm and exp_norm not in pred_norm and pred_norm not in exp_norm:
                    crop_matches_parcel = False

            if not crop_matches_parcel:
                photo_aligned = False  # Photo does NOT match this parcel if crop conflicts!

            # Inference sees a disk filename; previews need the owned asset
            # reference (or indexed library filename) used to authorize access.
            if img_record:
                vision_result["image_filename"] = img_record["filename"]
            vision_result["photo_association_verified"] = photo_aligned
            vision_result["crop_matches_parcel"] = crop_matches_parcel
            vision_result["expected_crop"] = expected_crop
            vision_result["coordinate_containment"] = vision_coordinate_containment
            vision_result["location_source"] = (img_record or {}).get("location_source", "provided dataset metadata")
            context["vision_result"] = vision_result
            context["vision_confidence"] = vision_result.get("confidence", 0.0)
            context["crop_matches_parcel"] = crop_matches_parcel
            context["expected_crop"] = expected_crop

            return {
                "predicted_crop": vision_result.get("final_verified_crop"),
                "crop_matches_parcel": crop_matches_parcel,
                "expected_crop": expected_crop,
                "confidence": vision_result.get("confidence"),
                "shannon_entropy": vision_result.get("shannon_entropy"),
                "has_image": vision_result.get("has_image", False),
                "actual_execution_model": (vision_result.get("teacher_model") if vision_result.get("escalated_to_teacher") else vision_result.get("student_model")) if vision_result.get("has_image") else "Vision skipped: no matched photo",
                "is_independent_teacher": vision_result.get("is_independent_teacher", False),
                "teacher_source": vision_result.get("teacher_source")
            }

        elif stype == "VERIFICATION_ESCALATION":
            selected_route = route_decision["selected_route"]
            vision_result = context["vision_result"] or {}
            img_record = context.get("img_record")
            img_path = img_record["filepath"] if img_record else None

            if "Teacher" in selected_route and img_path:
                if not vision_result.get("escalated_to_teacher"):
                    vision_result = self.vision.predict_crop(
                        img_path,
                        simulate_ood=context["simulate_unsupported_crop"],
                        force_escalate=True
                    )
                    vision_result["image_filename"] = img_record["filename"]
                    exp_crop = context.get("expected_crop")
                    pred_c = vision_result.get("final_verified_crop")
                    crop_m = True
                    if exp_crop and pred_c:
                        exp_n = exp_crop.lower().split("(")[0].strip()
                        pred_n = pred_c.lower().split("(")[0].strip()
                        if exp_n != pred_n and exp_n not in pred_n and pred_n not in exp_n:
                            crop_m = False
                    vision_result["crop_matches_parcel"] = crop_m
                    vision_result["expected_crop"] = exp_crop
                    vision_result["photo_association_verified"] = bool(crop_m and (context.get("vision_result") or {}).get("photo_association_verified"))
                    context["crop_matches_parcel"] = crop_m
                    context["vision_result"] = vision_result
                escalation_decision = "ESCALATED_TO_TEACHER"
            elif not vision_result.get("has_image"):
                escalation_decision = "PHOTO_ABSENT_CANNOT_ESCALATE"
            else:
                escalation_decision = "CONFIDENT_STUDENT_ACCEPTED"

            if "crop_matches_parcel" not in vision_result:
                vision_result["crop_matches_parcel"] = context.get("crop_matches_parcel", True)
                vision_result["expected_crop"] = context.get("expected_crop")

            if context.get("simulate_unsupported_crop"):
                context["final_crop"] = "Unclassified Alien Weed / Out-of-Distribution Flora"
                context["final_stage"] = "unclassified"
            elif not vision_result.get("has_image"):
                # Strictly refuse to fabricate crop perception when no field photograph exists
                context["final_crop"] = None
                context["final_stage"] = None
            else:
                context["final_crop"] = vision_result.get("final_verified_crop")
                context["final_stage"] = vision_result.get("final_verified_stage")

            return {
                "escalation_decision": escalation_decision,
                "final_crop": context["final_crop"],
                "final_stage": context["final_stage"],
                "actual_execution_model": (vision_result.get("teacher_model") if vision_result.get("escalated_to_teacher") else vision_result.get("student_model")) if vision_result.get("has_image") else "Vision skipped: no matched photo",
                "is_independent_teacher": vision_result.get("is_independent_teacher", False),
                "teacher_source": vision_result.get("teacher_source")
            }

        elif stype == "RAG_KNOWLEDGE":
            final_crop = context.get("final_crop")
            final_stage = context.get("final_stage")

            if not final_crop:
                # No verified field crop perception available for this survey
                target_survey_label = context.get("survey_no") or "Unspecified"
                advisory_result = {
                    "crop": None,
                    "growth_stage": None,
                    "found": False,
                    "source_grounded": False,
                    "verdict": "NO_VERIFIED_CROP_NO_ADVISORY",
                    "advisory_title": f"No Agronomy Advisory Available for Survey {target_survey_label}",
                    "fertilizer_schedule": None,
                    "water_management": None,
                    "pest_management": None,
                    "citation_source": None,
                    "retrieval_method": "FAISS_Vector_Search",
                    "similarity_score": 0.0,
                    "notice": f"Survey {target_survey_label} has no verified field crop on record. System strictly refuses to generate ungrounded fertilizer advisory."
                }
            else:
                advisory_result = self.knowledge.get_advisory(final_crop, final_stage or "full_growth")

            context["advisory_result"] = advisory_result
            return {
                "actual_execution_model": "Local agronomy corpus retrieval",
                "crop_advised": final_crop,
                "growth_stage": final_stage,
                "citation": advisory_result.get("citation_source")
            }

        elif stype == "TRUST_SYNTHESIS":
            doc_claims = context["doc_claims"] or {}
            reg_check = context["reg_check"] or {}
            parcel_gis = context["parcel_gis"]
            img_record = context["img_record"]
            extent_check = context["extent_check"] or {}
            spatial_constraints = context["spatial_constraints"] or {}
            vision_result = context["vision_result"] or {}

            has_land_doc = bool(doc_claims.get("found", False))
            has_reg = bool(reg_check.get("registry_found", False) and reg_check.get("official_owner"))
            # ownership_verified: True when document owner matches the revenue registry record.
            # Authoritative government record flag is NOT required — demo benchmark matches count.
            direct_owner_match = bool(reg_check.get("owner_match", False) and has_reg)
            is_authoritative_reg = bool(has_reg and reg_check.get("is_authoritative_government_record", False))
            has_parcel = (parcel_gis is not None)
            # Credit any valid uploaded/indexed photo for vision evidence (association
            # is hard-locked to False for user-uploaded images due to unverified coordinates).
            has_photo = bool(vision_result.get("has_image", False))

            wf_type = context.get("workflow_type")
            if wf_type == "ENVIRONMENTAL_BUFFER_AUDIT":
                has_parcel = (parcel_gis is not None)
                geom_valid = bool(has_parcel and spatial_constraints.get("geometry_valid", False))
                water_conflict = bool(spatial_constraints.get("waterbody_buffer_conflict", False))

                candidate_payload = {
                    "survey_number": str(context["survey_no"]) if context["survey_no"] else "UNSPECIFIED",
                    "village": context["village"],
                    "extracted_attributes": {
                        "registered_owner": reg_check.get("official_owner"),
                        "document_owner": doc_claims.get("extracted_owner"),
                        "ownership_verified": bool(reg_check.get("owner_match", False) and has_land_doc and has_reg),
                        "ownership_status": "OWNERSHIP_VERIFIED_MATCH" if bool(reg_check.get("owner_match", False) and has_land_doc and has_reg) else reg_check.get("owner_verification_status", "NOT_EVALUATED_GEOMETRY_AUDIT"),
                        "demo_record_match": bool(reg_check.get("owner_match", False) and has_land_doc and has_reg),
                        "is_authoritative_government_record": bool(reg_check.get("is_authoritative_government_record", False)),
                        "parcel_geometry_verified": geom_valid,
                        "gis_area_acres": parcel_gis.get("area_acres") if parcel_gis else None,
                        "predicted_crop": context.get("final_crop"),
                        "growth_stage": context.get("final_stage")
                    },
                    "deterministic_spatial_checks": {
                        "spatial_extent_verified": geom_valid,
                        "waterbody_buffer_compliant": (not water_conflict) if parcel_gis else False,
                        "deterministic_spatial_verified": geom_valid and ((not water_conflict) if parcel_gis else False)
                    }
                }
                trust_result = self.trust_engine.evaluate_trust(
                    vision_confidence=vision_result.get("final_confidence", vision_result.get("confidence", 0.0)) if has_photo else 0.0,
                    is_supported_crop=bool(context.get("final_crop") and not context.get("simulate_unsupported_crop")),
                    doc_registry_match=bool(reg_check.get("owner_match", False)) if (has_land_doc and has_reg) else True,
                    spatial_extent_match=geom_valid,
                    waterbody_conflict=water_conflict,
                    has_field_photo=has_photo,
                    has_land_doc=has_land_doc,
                    has_registry=has_parcel,
                    output_payload=candidate_payload,
                    workflow_type="ENVIRONMENTAL_BUFFER_AUDIT"
                )
                context["trust_result"] = trust_result
                return {
                    "actual_execution_model": "FARMSYNC local trust engine",
                    "trust_decision": trust_result.get("decision"),
                    "fts_score": trust_result.get("fts_score")
                }

            doc_provided = bool(context.get("document_path"))
            doc_verified = bool(reg_check.get("document_verified", False))
            doc_mismatch = bool(reg_check.get("document_mismatch", False) or (doc_provided and not doc_verified))
            doc_mismatch_reason = reg_check.get("details")

            if context.get("simulate_conflict"):
                doc_reg_match = False
                spatial_match = False
            elif doc_mismatch:
                doc_reg_match = False
                spatial_match = False
            elif doc_verified:
                doc_reg_match = bool(reg_check.get("owner_match", False) or reg_check.get("demo_record_match", False)) if has_reg else False
                spatial_match = (extent_check.get("verification_status") == "MATCH" or reg_check.get("extent_match", False))
            elif has_land_doc:
                # Accept demo registry match as a positive consistency signal
                doc_reg_match = bool(reg_check.get("owner_match", False) or reg_check.get("demo_record_match", False)) if has_reg else False
                spatial_match = (extent_check.get("verification_status") == "MATCH")
            else:
                # No document: use demo registry presence as a partial positive signal
                doc_reg_match = bool(has_reg and reg_check.get("owner_match", False))
                spatial_match = bool(has_parcel and spatial_constraints.get("geometry_valid", False))

            # Ownership verified = registry owner match (no government record requirement)
            if doc_mismatch:
                has_demo_match = False
                ownership_verified = False
                ownership_status = "DOCUMENT_MISMATCH_REJECT"
            else:
                has_demo_match = bool(direct_owner_match and has_land_doc)
                ownership_verified = direct_owner_match   # True when doc owner == registry owner
                ownership_status = (
                    "OWNERSHIP_VERIFIED_MATCH"
                    if direct_owner_match
                    else reg_check.get("owner_verification_status", "UNVERIFIED")
                )
            candidate_payload = {
                "survey_number": str(context["survey_no"]) if context["survey_no"] else "UNSPECIFIED",
                "village": context["village"],
                "extracted_attributes": {
                    "registered_owner": reg_check.get("official_owner"),
                    "document_owner": doc_claims.get("extracted_owner"),
                    "ownership_verified": ownership_verified,
                    "ownership_status": ownership_status,
                    "demo_record_match": has_demo_match,
                    "is_authoritative_government_record": bool(reg_check.get("is_authoritative_government_record", False)),
                    "parcel_geometry_verified": spatial_match,
                    "gis_area_acres": parcel_gis.get("area_acres") if parcel_gis else None,
                    "predicted_crop": context.get("final_crop"),
                    "growth_stage": context.get("final_stage"),
                    "crop_matches_parcel": context.get("crop_matches_parcel", True),
                    "expected_crop": context.get("expected_crop"),
                    "crop_mismatch_detected": bool(not context.get("crop_matches_parcel", True)),
                    "document_provided": doc_provided,
                    "document_verified": doc_verified,
                    "document_mismatch": doc_mismatch,
                    "survey_match": reg_check.get("survey_match", False),
                    "extent_match": reg_check.get("extent_match", False),
                    "doc_survey_no": reg_check.get("doc_survey_no"),
                    "expected_acres": reg_check.get("official_extent_acres")
                },
                "deterministic_spatial_checks": {
                    "spatial_extent_verified": spatial_match,
                    "waterbody_buffer_compliant": not spatial_constraints.get("waterbody_buffer_conflict", False) if parcel_gis else False
                }
            }

            trust_result = self.trust_engine.evaluate_trust(
                vision_confidence=vision_result.get("final_confidence", vision_result.get("confidence", 0.0)) if has_photo else 0.0,
                is_supported_crop=bool(context.get("final_crop") and not context["simulate_unsupported_crop"]),
                doc_registry_match=doc_reg_match,
                spatial_extent_match=spatial_match,
                waterbody_conflict=spatial_constraints.get("waterbody_buffer_conflict", False) if parcel_gis else False,
                has_field_photo=has_photo,
                has_land_doc=bool(has_land_doc or doc_provided),
                # Use demo registry presence (not only authoritative government records)
                # so uploads against known parcels receive proper evidence-coverage credit.
                has_registry=bool(has_reg and has_parcel),
                output_payload=candidate_payload,
                workflow_type=wf_type,
                crop_conflict=bool(has_photo and not context.get("crop_matches_parcel", True)),
                doc_mismatch=doc_mismatch,
                doc_mismatch_reason=doc_mismatch_reason
            )
            context["trust_result"] = trust_result
            return {
                "actual_execution_model": "FARMSYNC local trust engine",
                "trust_decision": trust_result.get("decision"),
                "fts_score": trust_result.get("fts_score")
            }

        return {}
