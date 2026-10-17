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
        self.target_survey_no = target_survey_no
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
            "total_nodes": len(self.nodes),
            "planner_source": getattr(self, "planner_source", "VALIDATED_DOMAIN_TEMPLATE"),
            "planning_usage": getattr(self, "planning_usage", {})
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
    @staticmethod
    def extract_buffer_distance(query):
        match = re.search(r"(\d+(?:\.\d+)?)\s*(km|metres?|meters?|m)\s*(?:waterbody\s*)?buffer", query, re.I)
        if not match:
            match = re.search(r"buffer\s*(?:of|:|=)?\s*(\d+(?:\.\d+)?)\s*(km|metres?|meters?|m)\b", query, re.I)
        if not match:
            return 50.0
        value = float(match[1]) * (1000 if match[2].lower() == "km" else 1)
        if not 0 < value <= 10000:
            raise ValueError("Buffer must be greater than 0 and at most 10000 metres")
        return value

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

    @staticmethod
    def extract_survey_number(query: str) -> Optional[str]:
        """
        Extracts survey numbers and subdivision identifiers from diverse cadastral formats:
        - "Survey Number 384", "Survey No. 384/1A", "Survey #384", "Survey 384"
        - "S.No. 384/1", "S.No 384", "SNo 384", "S. No. 384", "Sy. No. 384", "Syno 384"
        - "S.F. No. 384", "SF No. 384", "SFNo 384" (Survey Field Number)
        - "R.S. No. 384", "RS No. 384" (Re-survey Number)
        - "Cadastral Parcel 384", "Parcel No. 384", "Parcel 384", "Plot 384"
        - Subdivisions: 384/1, 384/1A, 384-1B, 176/2, 381/1, etc.
        """
        patterns = [
            # Formats with prefix: Survey, S.No, S.F. No, SF No, Sy. No, RS No, Cadastral Parcel, Parcel, Plot
            r'(?:(?:survey|re-?survey|cadastral\s*parcel|parcel|plot)\s*(?:number|num|no\.?|#|id)?|s\.?\s*f\.?\s*no\.?|s\.?\s*y\.?\s*no\.?|r\.?\s*s\.?\s*no\.?|s\.?\s*no\.?)\s*[:#-]?\s*([0-9]+(?:[\/\-_][0-9]+[A-Za-z0-9]*)?)',
            # Suffix formats: e.g. "384 Survey Number" or "384/1 S.No"
            r'\b([0-9]+(?:[\/\-_][0-9]+[A-Za-z0-9]*)?)\s*(?:survey\s*(?:number|no\.?|#)?|s\.?no\.?)',
            # Key-value or direct survey assignment
            r'\bsurvey\s*[:=]\s*([0-9]+(?:[\/\-_][0-9]+[A-Za-z0-9]*)?)'
        ]
        for pat in patterns:
            m = re.search(pat, query, re.IGNORECASE)
            if m:
                clean = m.group(1).strip()
                clean = re.sub(r'[\.,;]$', '', clean)
                return clean
        return None

    @staticmethod
    def extract_village_name(query: str) -> str:
        """
        Extracts multi-word village names from natural language queries:
        - "in Keela Thattaparai village", "for Keelathattaparai village"
        - "village of Keela Thattaparai", "village: Keelathattaparai"
        - "village Keelathattaparai"
        - "Mela Thattaparai village"
        Defaults to "Keelathattaparai" if no village entity is found.
        """
        # Pattern 1: Multi-word name preceding 'village' with preposition (in/at/for/of)
        m1 = re.search(r'(?:\bin|\bat|\bfor|\bof)\s+([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)\s+village\b', query)
        if m1:
            name = m1.group(1).strip()
            name_clean = re.sub(r'^(the|in|at|of|for)\s+', '', name, flags=re.IGNORECASE).strip()
            if len(name_clean) > 2 and name_clean.lower() not in ["survey", "parcel", "document", "this", "target"]:
                return name_clean

        # Pattern 2: Name following 'village of' or 'village:' (Title Cased)
        m2 = re.search(r'\bvillage\s*(?:of|:)\s+([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)', query)
        if m2:
            name = m2.group(1).strip()
            name_clean = re.sub(r'\s+(?:panchayat|taluk|district|village|,|\.|\bin\b|\bwith\b|\bfor\b|\bidentify\b|\bverify\b|\bcheck\b|\busing\b|\bparcels?\b).*$', '', name, flags=re.IGNORECASE).strip()
            if len(name_clean) > 2 and name_clean.lower() not in ["survey", "parcel", "document", "this", "target", "the"]:
                return name_clean

        # Pattern 3: Name directly following 'village <Name>' (Title Cased, e.g. "village Keelathattaparai")
        m3 = re.search(r'\bvillage\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', query)
        if m3:
            name = m3.group(1).strip()
            stopwords = {"parcels", "boundary", "land", "records", "level", "administration", "officer", "survey"}
            if len(name) > 2 and name.lower() not in stopwords:
                return name

        # Pattern 4: Any Title Cased word(s) immediately preceding 'village' (not stopwords)
        m4 = re.search(r'\b([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)\s+village\b', query)
        if m4:
            words = m4.group(1).split()
            stopwords = {"analyze", "examine", "check", "verify", "inspect", "audit", "find", "identify", "evaluate", "review", "parcel", "the", "this", "target", "using", "supplied"}
            clean_words = [w for w in words if w.lower() not in stopwords]
            if clean_words:
                return " ".join(clean_words)

        # Pattern 5: Explicit 'in <Name> (panchayat|taluk|district)'
        m5 = re.search(r'\bin\s+([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)\s+(?:panchayat|taluk|district)\b', query)
        if m5:
            name = m5.group(1).strip()
            if len(name) > 2:
                return name

        return "Keelathattaparai"

    def compile(self, query: str, plan=None) -> TaskGraph:
        """
        Compiles user query into a typed executable TaskGraph DAG.
        Extracts key entities (survey number, village, document name, intent) without fabrication.
        """
        # Entity extraction via robust regex patterns
        survey_no = self.extract_survey_number(query)
        village = self.extract_village_name(query)

        # Document filename extraction
        doc_match = re.search(r'([A-Za-z0-9_\-\(\)\s]+\.pdf)', query, re.IGNORECASE)
        target_doc = doc_match.group(1).strip() if doc_match else None

        # Intent classification
        q_lower = query.lower()
        if any(k in q_lower for k in ["discrepancy", "unmatched", "extent difference", "acquisition progress"]):
            workflow_type = "LAND_DISCREPANCY_INTELLIGENCE"
            # The executor supports single-parcel checks, not batch document extraction.
            specs = self.PARCEL_ADVISORY_SPECS
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

        if plan and not plan.get("fallback"):
            from farmsync.router.planner import CAPABILITIES, validate_tasks
            selected = validate_tasks({"tasks": plan["tasks"]})
            if set(selected) <= {"spatial", "trust"}:
                graph.workflow_type = "ENVIRONMENTAL_BUFFER_AUDIT"
            specs = []
            for key in selected:
                deps = []
                if key == "registry":
                    deps = ["document"]
                elif key == "spatial":
                    deps = [t for t in ("document", "registry") if t in selected]
                elif key == "escalation":
                    deps = ["vision"]
                elif key == "advisory":
                    deps = ["escalation"]
                elif key == "trust":
                    deps = [t for t in selected if t != "trust"]
                specs.append({"id": key, "name": CAPABILITIES[key][1], "type": CAPABILITIES[key][0], "deps": deps})
            graph.planner_source = plan["source"]
            graph.planning_usage = plan.get("usage", {})

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


# Module-level aliases for direct utility access
extract_survey_number = TaskGraphCompiler.extract_survey_number
extract_village_name = TaskGraphCompiler.extract_village_name
