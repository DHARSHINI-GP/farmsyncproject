import re
from typing import Dict, Any, List, Optional, Set
from collections import deque


class TaskNode:
    """
    Executable Node in the FARMSYNC Task Graph DAG.
    Tracks dependencies, inputs/outputs, runtime execution state, router decisions, and outputs.
    """
    def __init__(
        self,
        task_id: str,
        name: str,
        subtask_type: str,
        deps: Optional[List[str]] = None,
        inputs: Optional[List[str]] = None,
        outputs: Optional[List[str]] = None,
        description: str = ""
    ):
        self.id = task_id
        self.name = name
        self.subtask_type = subtask_type
        self.deps = deps or []
        self.inputs = inputs or []
        self.outputs = outputs or []
        self.description = description

        # Runtime execution state
        self.status = "PENDING"  # PENDING -> RUNNING -> COMPLETED / SKIPPED / FAILED
        self.selected_route: Optional[str] = None
        self.route_type: Optional[str] = None
        self.route_score: Optional[float] = None
        self.cost_usd: float = 0.0
        self.latency_ms: int = 0
        self.rationale: Optional[str] = None
        self.result: Optional[Any] = None
        self.error: Optional[str] = None

    def mark_running(self):
        self.status = "RUNNING"

    def mark_completed(
        self,
        result: Any,
        cost_usd: float,
        latency_ms: int,
        route_decision: Optional[Dict[str, Any]] = None
    ):
        self.status = "COMPLETED"
        self.result = result
        self.cost_usd = round(cost_usd, 6)
        self.latency_ms = latency_ms
        if route_decision:
            self.selected_route = route_decision.get("selected_route")
            self.route_type = route_decision.get("route_type")
            self.route_score = route_decision.get("route_score")
            self.rationale = route_decision.get("routing_rationale")

    def mark_skipped(self, reason: str = ""):
        self.status = "SKIPPED"
        self.result = {"skipped": True, "reason": reason}

    def mark_failed(self, error: str):
        self.status = "FAILED"
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.subtask_type,
            "deps": self.deps,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "status": self.status,
            "selected_route": self.selected_route,
            "route_type": self.route_type,
            "route_score": self.route_score,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "rationale": self.rationale,
            "has_result": self.result is not None,
            "result": self.result,
            "error": self.error
        }

    def __getitem__(self, item):
        return self.to_dict()[item]

    def get(self, item, default=None):
        return self.to_dict().get(item, default)


class TaskGraph:
    """
    Executable Directed Acyclic Graph (DAG) for multimodal geospatial tasks.
    Enforces topological execution, acyclicity verification, and dependency satisfaction.
    """
    def __init__(
        self,
        workflow_type: str,
        query: str,
        target_survey_no: Optional[str] = None,
        explicit_survey_provided: bool = False,
        target_village: str = "Keelathattaparai",
        target_document: Optional[str] = None
    ):
        self.workflow_type = workflow_type
        self.query = query
        self.target_survey_no = target_survey_no or "384"
        self.explicit_survey_provided = explicit_survey_provided
        self.target_village = target_village
        self.target_document = target_document

        self.nodes: Dict[str, TaskNode] = {}
        self.node_order: List[str] = []
        self.adjacency: Dict[str, List[str]] = {}  # parent_id -> list of child_ids

    def add_node(self, node: TaskNode):
        self.nodes[node.id] = node
        if node.id not in self.node_order:
            self.node_order.append(node.id)
        if node.id not in self.adjacency:
            self.adjacency[node.id] = []
        for dep in node.deps:
            if dep not in self.adjacency:
                self.adjacency[dep] = []
            self.adjacency[dep].append(node.id)

    def topological_sort(self) -> List[TaskNode]:
        """
        Calculates execution order using Kahn's algorithm with stable tie-breaking.
        Verifies that the graph is an acyclic DAG.
        """
        in_degree = {nid: len(node.deps) for nid, node in self.nodes.items()}
        ready = [nid for nid in self.node_order if in_degree[nid] == 0]
        order: List[TaskNode] = []

        while ready:
            curr_id = ready.pop(0)
            order.append(self.nodes[curr_id])
            for child_id in self.adjacency.get(curr_id, []):
                in_degree[child_id] -= 1
                if in_degree[child_id] == 0:
                    ready.append(child_id)
                    ready.sort(key=lambda nid: self.node_order.index(nid))

        if len(order) != len(self.nodes):
            raise ValueError(f"Cycle detected in TaskGraph DAG! Ordered {len(order)} of {len(self.nodes)} nodes.")
        return order

    def are_deps_satisfied(self, task_id: str, completed_task_ids: Set[str]) -> bool:
        node = self.nodes.get(task_id)
        if not node:
            return False
        return all(dep in completed_task_ids for dep in node.deps)

    def get_node(self, task_id: str) -> Optional[TaskNode]:
        return self.nodes.get(task_id)

    def to_dict(self) -> Dict[str, Any]:
        ordered = self.topological_sort()
        return {
            "workflow_type": self.workflow_type,
            "target_survey_no": self.target_survey_no,
            "explicit_survey_provided": self.explicit_survey_provided,
            "target_village": self.target_village,
            "target_document": self.target_document,
            "subtasks": [n.to_dict() for n in ordered],
            "is_dynamic_dag": True,
            "total_nodes": len(self.nodes)
        }

    # Dict-like compatibility interface
    def __getitem__(self, item):
        return self.to_dict()[item]

    def get(self, item, default=None):
        return self.to_dict().get(item, default)

    def __contains__(self, item):
        return item in self.to_dict()

    def keys(self):
        return self.to_dict().keys()

    def values(self):
        return self.to_dict().values()

    def items(self):
        return self.to_dict().items()


class TaskGraphCompiler:
    """
    Task Graph Compiler for FARMSYNC.
    Deconstructs natural-language multimodal requests into a typed, executable Directed Acyclic Graph (DAG).
    Builds verified dependency graphs with input/output contracts.
    """

    # Pre-validated standard workflow templates for FarmwiseAI tasks
    PARCEL_ADVISORY_SPECS = [
        {"id": "task_1", "name": "Extract Survey & Claims", "type": "DOCUMENT_OCR", "deps": [], "inputs": ["document_path", "survey_no"], "outputs": ["doc_claims"]},
        {"id": "task_2", "name": "Registry Cross-Check", "type": "DATABASE_JOIN", "deps": ["task_1"], "inputs": ["doc_claims"], "outputs": ["reg_check"]},
        {"id": "task_3", "name": "Deterministic GIS Spatial Check", "type": "GEOSPATIAL_GIS", "deps": ["task_2"], "inputs": ["survey_no", "doc_claims"], "outputs": ["parcel_gis", "spatial_constraints", "extent_check"]},
        {"id": "task_4", "name": "Field Crop Perception", "type": "VISION_STUDENT", "deps": [], "inputs": ["survey_no"], "outputs": ["img_record", "vision_result", "vision_confidence"]},
        {"id": "task_5", "name": "Multimodal Escalation Check", "type": "VERIFICATION_ESCALATION", "deps": ["task_4"], "inputs": ["vision_result", "vision_confidence"], "outputs": ["escalation_decision", "final_crop", "final_stage"]},
        {"id": "task_6", "name": "Agronomy Advisory Retrieval", "type": "RAG_KNOWLEDGE", "deps": ["task_5"], "inputs": ["final_crop", "final_stage"], "outputs": ["advisory_result"]},
        {"id": "task_7", "name": "Evidence Graph & Trust Score Synthesis", "type": "TRUST_SYNTHESIS", "deps": ["task_3", "task_6"], "inputs": ["doc_claims", "reg_check", "parcel_gis", "spatial_constraints", "extent_check", "vision_result", "advisory_result"], "outputs": ["trust_result", "evidence_graph", "verified_result_object"]}
    ]

    DISCREPANCY_SPECS = [
        {"id": "task_1", "name": "Extract All Document Parcels", "type": "DOCUMENT_OCR", "deps": [], "inputs": ["document_path"], "outputs": ["doc_parcels"]},
        {"id": "task_2", "name": "Batch Cadastral Intersection", "type": "GEOSPATIAL_GIS", "deps": ["task_1"], "inputs": ["doc_parcels"], "outputs": ["intersection_results"]},
        {"id": "task_3", "name": "Extent Delta Calculation", "type": "GEOSPATIAL_GIS", "deps": ["task_2"], "inputs": ["intersection_results"], "outputs": ["extent_deltas"]},
        {"id": "task_4", "name": "Discrepancy Reporting & Flagging", "type": "TRUST_SYNTHESIS", "deps": ["task_3"], "inputs": ["extent_deltas"], "outputs": ["discrepancy_report"]}
    ]

    BUFFER_AUDIT_SPECS = [
        {"id": "task_1", "name": "Cadastral Parcel Lookup", "type": "GEOSPATIAL_GIS", "deps": [], "inputs": ["survey_no"], "outputs": ["parcel_gis"]},
        {"id": "task_2", "name": "Waterbody Buffer Analysis", "type": "GEOSPATIAL_GIS", "deps": ["task_1"], "inputs": ["parcel_gis"], "outputs": ["waterbody_buffer"]},
        {"id": "task_3", "name": "Road Network Transit Calculation", "type": "GEOSPATIAL_GIS", "deps": ["task_1"], "inputs": ["parcel_gis"], "outputs": ["transit_route"]},
        {"id": "task_4", "name": "Environmental Compliance Synthesis", "type": "TRUST_SYNTHESIS", "deps": ["task_2", "task_3"], "inputs": ["waterbody_buffer", "transit_route"], "outputs": ["compliance_report"]}
    ]

    def compile(self, query: str) -> TaskGraph:
        """
        Compiles user query into a typed executable TaskGraph DAG.
        Extracts key entities (survey number, village, document name, intent) without fabrication.
        """
        # Entity extraction via regex patterns
        survey_match = re.search(r'survey\s*(?:number|no\.?|#)?\s*([0-9]+(?:/[0-9]+[A-Za-z]*)?)', query, re.IGNORECASE)
        survey_no = survey_match.group(1) if survey_match else None

        village_match = re.search(r'village\s+([A-Za-z]+)', query, re.IGNORECASE)
        village = village_match.group(1) if village_match else "Keelathattaparai"

        # Document filename extraction
        doc_match = re.search(r'([A-Za-z0-9_\-\(\)\s]+\.pdf)', query, re.IGNORECASE)
        target_doc = doc_match.group(1).strip() if doc_match else None

        # Intent classification
        q_lower = query.lower()
        if any(k in q_lower for k in ["discrepancy", "unmatched", "extent difference", "acquisition progress"]):
            workflow_type = "LAND_DISCREPANCY_INTELLIGENCE"
            specs = self.DISCREPANCY_SPECS
        elif any(k in q_lower for k in ["waterbody", "buffer", "runoff", "environmental", "geofence"]):
            workflow_type = "ENVIRONMENTAL_BUFFER_AUDIT"
            specs = self.BUFFER_AUDIT_SPECS
        else:
            workflow_type = "PARCEL_EVIDENCE_ADVISORY"
            specs = self.PARCEL_ADVISORY_SPECS

        graph = TaskGraph(
            workflow_type=workflow_type,
            query=query,
            target_survey_no=survey_no,
            explicit_survey_provided=survey_no is not None,
            target_village=village,
            target_document=target_doc
        )

        for spec in specs:
            node = TaskNode(
                task_id=spec["id"],
                name=spec["name"],
                subtask_type=spec["type"],
                deps=spec["deps"],
                inputs=spec.get("inputs", []),
                outputs=spec.get("outputs", []),
                description=spec.get("name", "")
            )
            graph.add_node(node)

        return graph
