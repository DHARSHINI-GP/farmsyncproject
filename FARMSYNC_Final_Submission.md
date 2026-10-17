> **Historical proposal / submission draft.** This document includes superseded architecture and unverified cloud claims. The organizer access guide and [HACKATHON_READINESS.md](HACKATHON_READINESS.md) govern the current implementation and live acceptance status.

# FARMSYNC
### Evidence-Driven Adaptive AI Orchestration for Geospatial Intelligence

---

| Metadata Item | Specification |
| :--- | :--- |
| **Challenge** | Task 1 — Multi-Model, Multimodal and Agentic AI System |
| **Registration ID** | **TCPC-2026-00071** |
| **Project Title** | **FARMSYNC** — Evidence-Driven Adaptive AI Orchestration for Geospatial Intelligence |
| **Team Members** | **Safi A (Lead)**, **Mohamed asfaq S**, **Sooraj TS** |
| **Prototype Window** | 2–3 weeks after shortlisting; final integration depends on data package and model/cloud credits. |

---

### Why this is a strong Task 1 fit

* **Multi-Model Orchestration**: FARMSYNC dynamically orchestrates heterogeneous AI models across distinct task tiers (e.g., GPT-4o / Claude 3.5 Sonnet for complex planning, Gemini 1.5 Pro for verification, and open-weight Qwen2.5-VL for low-cost vision perception).
* **Multimodal Intelligence**: The system ingests text queries, scanned land records (Patta/acquisition notices), field ground photographs, and PostGIS vector spatial layers seamlessly.
* **Agentic Control & Routing**: Uses an explicit Verified-Utility Router ($\text{Quality} - \text{Cost} - \text{Latency} - \text{Risk}$) to select models/tools and execute bounded escalation or abstention when evidence is insufficient.
* **Grounded & Deterministic-First**: Spatial containment, distance checks, and numeric area math are computed by deterministic tools (PostGIS / Python) rather than guessed by language models.
* **Observable Telemetry**: The UI displays live task graphs, model routing rationale, execution latency, estimated API costs, and evidence graphs, making agent behavior fully transparent to evaluators.

---

## 1. Chosen Challenge, Title, and Objective

### Project Title
**FARMSYNC — Evidence-Driven Adaptive AI Orchestration for Geospatial Intelligence**

### Objective
Build and demonstrate a reusable, generic agentic AI system that accepts text requests, land documents, field photographs, and spatial datasets; compiles requests into execution graphs; routes subtasks across proprietary and open-weight models; verifies claims via deterministic tools; and produces a source-traceable final answer with visible routing telemetry.

### Primary Demonstration Scenario
> *"Using the supplied land document and field photograph for Devapura village, identify Survey Number 144/3B, verify its parcel boundary and registered owner, predict the crop type and growth stage from the field image, retrieve the applicable fertilizer advisory, perform relevant spatial proximity checks against restricted waterbody zones, and return a source-traceable verified recommendation."*

#### What FARMSYNC Executes:
1. **Task Compiler**: Converts the query into a typed 7-task execution graph with explicit dependencies.
2. **Document & Registry Join**: Extracts owner and survey details from scanned PDF, matching with registry SQL records.
3. **Open-Weight Vision Perception**: Passes field photo to lightweight open-weight VLM (Qwen2.5-VL) for initial crop/stage classification.
4. **Deterministic Spatial Verification**: Invokes PostGIS (`ST_Contains`, `ST_Distance`) to check parcel boundary containment and road/waterbody buffers.
5. **Trust Score Evaluation**: Calculates Model-Agnostic Trust Score ($FTS$). If confidence/evidence is low, automatically escalates to Proprietary VLM (Claude 3.5 Sonnet).
6. **RAG Advisory Synthesis**: Retrieves stage-specific fertilizer advisory from indexed agricultural documents.
7. **Traceable Output**: Returns final verified result alongside interactive spatial map, evidence graph DAG, and cost/latency telemetry.

> **Core Idea**  
> *The Planner compiles the workflow. The Tools provide deterministic facts. The Router optimizes verified utility. The Trust Engine decides whether the answer is sufficiently proven.*

---

## 2. Problem Understanding

Complex geospatial and agricultural operations depend on heterogeneous data sources (scanned paper documents, ground photos, satellite vectors, registry databases). Single-model prompts fail because no single model is simultaneously economical, deterministic at spatial math, and perfectly calibrated.

FARMSYNC addresses five core failure modes in current AI systems:
1. **Unverified Advisory**: Generates agricultural advice without traceable evidence from approved agronomy sources.
2. **Model Confidence Fallacy**: Vendor-reported confidence scores are uncalibrated and non-comparable across proprietary and open-source models.
3. **Deterministic Math Failure**: Relying on LLMs for geometric spatial calculations (area, distance, containment) introduces hallucinations.
4. **Opaque Routing & Cost Inefficiency**: Using premium models for routine OCR/perception wastes compute; static routing lacks adaptability.
5. **Forced Predictions**: Systems that lack an abstention mechanism generate hallucinated answers when evidence is missing or contradictory.

### Working Principle
$$\mathbf{Understand} \longrightarrow \mathbf{Compile\ Task\ Graph} \longrightarrow \mathbf{Route\ (Verified\ Utility)} \longrightarrow \mathbf{Ground\ \&\ Execute} \longrightarrow \mathbf{Verify\ (FTS)} \longrightarrow \mathbf{Accept\ /\ Escalate\ /\ Abstain}$$

If required evidence cannot be verified, FARMSYNC refuses to invent missing facts. It escalates to an alternate model route or explicitly abstains and flags for human review.

---

## 3. What We Propose to Build and Demonstrate

FARMSYNC delivers a complete AI orchestration workspace that turns multimodal geospatial requests into verified operational answers.

| Demo Feature | What the Evaluator Will See |
| :--- | :--- |
| **Multimodal Query Ingestion** | User uploads a land document PDF, ground field photo, and inputs a natural language query for Survey Number 144/3B. |
| **Dynamic Execution Graph** | Visual task DAG compiler panel showing 7 subtasks, dependencies, and real-time step execution status. |
| **Adaptive Model Routing** | Live telemetry showing routine perception routed to open-weight model (Qwen2.5-VL) and escalated complex tasks routed to proprietary models (GPT-4o / Claude 3.5 Sonnet). |
| **Deterministic Spatial Check** | PostGIS engine executing exact geometric area and distance buffer computations without LLM hallucination. |
| **Evidence Graph Provenance** | Interactive claim-to-source DAG mapping claims directly to source documents, SQL records, and spatial layers. |
| **Trust Engine & Bounded Recovery** | Trust Engine evaluating result; demonstrating automatic escalation on low confidence and explicit abstention on missing evidence. |
| **Unseen Request Benchmark** | Executing a completely different Land Acquisition Discrepancy query without altering orchestration codebase. |
| **Baseline Cost/Latency Comparison** | Live dashboard comparing FARMSYNC vs. Pure GPT-4o vs. Static Routing showing >50% cost savings with zero accuracy loss. |

---

## 4. Solution Approach, Architecture, Models and Technology

FARMSYNC strictly separates AI reasoning from deterministic spatial and database operations. 

```
                                  USER REQUEST
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │ TASK GRAPH COMPILER │
                            └──────────┬──────────┘
                                       │ typed subtasks
                                       ▼
                            ┌─────────────────────┐
                            │ CAPABILITY REGISTRY │
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │VERIFIED-UTILITY ROUTER│
                            └──────────┬──────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
      OPEN-WEIGHT MODEL        PROPRIETARY MODEL A      PROPRIETARY MODEL B
    (Qwen2.5-VL / Llama 3.2)   (GPT-4o / Claude 3.5)      (Gemini 1.5 Pro)
              │                        │                        │
              └────────────────────────┼────────────────────────┘
                                       ▼
                            ┌─────────────────────┐
                            │   GROUNDED TOOLS    │
                            │ PostGIS / SQL / RAG │
                            │ PaddleOCR / Python  │
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │   EVIDENCE GRAPH    │
                            └──────────┬──────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │    TRUST ENGINE     │
                            └──────────┬──────────┘
                                       │
               ┌───────────────────────┼───────────────────────┐
               ▼                       ▼                       ▼
            ACCEPT                  ESCALATE                 ABSTAIN
               │                       │                       │
               │                       ▼                       ▼
               │                Alternate Route          Human Review
               └───────────────────────┬───────────────────────┘
                                       ▼
                                VERIFIED RESULT
```

### 4.1 Core Technical Formulations

#### 1. Verified-Utility Router Policy
Instead of asking "which model is smartest?", the router optimizes expected utility after verification:

$$\text{Expected Verified Utility} = \text{Expected Verified Quality} - \lambda \cdot \text{Cost} - \mu \cdot \text{Latency} - \rho \cdot \text{Failure Risk} + \eta \cdot \text{Verification Gain}$$

#### 2. Model-Agnostic Trust Score ($FTS$)
Vendor confidence scores are uncalibrated. FARMSYNC computes trust from independent, observable evidence:

$$FTS = w_1 \cdot \text{Calibration} + w_2 \cdot \text{EvidenceCoverage} + w_3 \cdot \text{SourceConsistency} + w_4 \cdot \text{DeterministicValidation} + w_5 \cdot \text{OutputValidity} - w_6 \cdot \text{ConflictPenalty}$$

*Hyperparameter Safeguard*: Initial weights $w_1 \dots w_6$ are normalized via min-max feature scaling on an initial 20-sample validation set, defaulting to equal weights ($w_i = 1/6$) when initial sample size $N < 10$.

### 4.2 Agentic Control Loop
1. **Understand & Compile**: LLM converts user query into typed task DAG. *Fallback*: If malformed DAG is generated, system falls back to pre-validated linear template.
2. **Match Capabilities**: Query registry for available models, tools, and latency/cost specs.
3. **Route**: Select execution route maximizing Expected Verified Utility.
4. **Ground & Execute**: Run models for perception/synthesis; run PostGIS/SQL/Python for exact facts.
5. **Build Evidence Graph**: Construct in-memory DAG linking claims to source documents and GIS polygons.
6. **Verify & Recover**: Evaluate $FTS$. If $FTS \ge 0.85 \rightarrow \mathbf{ACCEPT}$; if $0.60 \le FTS < 0.85 \rightarrow \mathbf{ESCALATE}$; if $FTS < 0.60 \rightarrow \mathbf{ABSTAIN}$.

---

## 5. Main Components and Prototype Capabilities

| Component | Technology | Prototype Capability |
| :--- | :--- | :--- |
| **Task Graph Compiler** | FastAPI + OpenAI GPT-4o / Instructor | Deconstructs request into typed subtask DAG; includes automatic fallback to linear workflow templates. |
| **Capability Registry** | Python Registry Engine | Maintains dynamic performance, cost ($/1k tokens), latency, and capability profiles of available models/tools. |
| **Verified-Utility Router** | Lightweight Scored Policy Engine | Evaluates RouteScore per subtask to route work economically without quality loss. |
| **Document & OCR Engine** | PaddleOCR + PyMuPDF | Extracts structured text, survey numbers, and extents from scanned Patta/acquisition PDFs. |
| **Deterministic Spatial Engine** | PostgreSQL / PostGIS + GeoPandas | Performs exact polygon intersection (`ST_Contains`), distance buffers (`ST_Distance`), and area delta math. |
| **Open-Weight Vision Model** | Qwen2.5-VL-7B (vLLM / Ollama) | Low-cost first-pass crop classification, growth stage estimation, and visual feature extraction. |
| **Proprietary Multimodal VLM** | Claude 3.5 Sonnet / GPT-4o API | High-reasoning task planning, complex document-to-parcel resolution, and escalation verification. |
| **Agronomy RAG System** | LangChain / LlamaIndex + FAISS | Retrieves stage-appropriate fertilizer and crop management recommendations with page citations. |
| **Trust & Verification Engine** | Custom Python Engine | Computes $FTS$, checks deterministic constraints, and governs bounded escalation/abstention. |
| **Interactive Telemetry UI** | React.js + Leaflet GIS + Tailwind CSS | Displays synchronized map, task DAG execution trace, evidence graph, cost/latency counters, and baseline charts. |

---

## 6. Innovative and Exploratory Ideas

### 1. Refuse-to-Invent Principle (Bounded Abstention)
FARMSYNC guarantees that an ungrounded or contradictory claim will never be presented as verified advice:
* If land document owner differs from database registry owner, result is flagged as **`CONFLICT_DISCREPANCY`** rather than guessing.
* If field photo is blurry or out-of-distribution, student vision model returns low confidence, triggering **Proprietary VLM Escalation**.
* If alternate route also fails verification, system enters explicit **`ABSTAIN_HUMAN_REVIEW`** state.

### 2. In-Memory JSON Evidence Graph DAG
Rather than deploying heavy graph database infrastructure (Neo4j), FARMSYNC builds an in-memory Directed Acyclic Graph (DAG) JSON structure passed through shared execution state, enabling instant claim-to-source traceability:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "VerifiedResultObject",
  "properties": {
    "claim_id": "CLM-2026-DEV-144",
    "survey_number": "144/3B",
    "village": "Devapura",
    "extracted_owner": "Ramesh Kumar",
    "source_evidence": [
      { "type": "DOCUMENT_OCR", "ref": "Acquisition_04.pdf#P2", "value": "Ramesh Kumar", "confidence": 0.91 },
      { "type": "DATABASE_REGISTRY", "ref": "Land_Registry.parcels", "value": "Ramesh Kumar", "confidence": 1.0 }
    ],
    "deterministic_checks": {
      "postgis_containment_valid": true,
      "extent_mismatch_pct": 0.0,
      "waterbody_buffer_conflict": false
    },
    "trust_metrics": {
      "model_reported_confidence": 0.84,
      "task_trust_score_fts": 0.95,
      "verification_status": "VERIFIED_ACCEPTED"
    },
    "routing_telemetry": {
      "primary_model": "Qwen2.5-VL-7B",
      "escalation_model": "Claude-3.5-Sonnet",
      "was_escalated": true,
      "total_latency_ms": 1120,
      "estimated_cost_usd": 0.0038
    }
  }
}
```

### 3. Built-In Multi-Baseline Benchmarking
The UI includes real-time telemetry comparing **FARMSYNC vs. Premium-Only (GPT-4o) vs. Static Routing**, proving quality retention while demonstrating explicit cost and latency reductions.

---

## 7. Datasets, Maps, Documents, APIs and Model Access

| Resource | Role in FARMSYNC | Status / Requirement |
| :--- | :--- | :--- |
| **Cadastral Parcel GIS Layer** | Provides vector boundaries, survey numbers, and geometries for 1–2 sample villages. | Required (GeoJSON/Shapefile dataset) |
| **Land Record Documents** | Sample scanned Patta documents and land acquisition notices in PDF format. | Required (Sample PDF dataset) |
| **Field Ground Photographs** | Sample ground photographs of crops with metadata (location, date). | Required (Sample image dataset) |
| **Agronomy Advisory Corpus** | TNAU / ICAR crop advisory guides and fertilizer recommendation manuals. | Required (Reference PDFs) |
| **PostgreSQL + PostGIS** | Spatial database engine for deterministic geometric and distance calculations. | Local / Cloud container |
| **Open-Weight VLM (Qwen2.5-VL)** | Low-cost first-pass vision perception and OCR processing. | GPU Instance (AWS g5.xlarge / Ollama) |
| **Proprietary VLM APIs** | Primary task planning, complex synthesis, and secondary escalation verification. | API Access (OpenAI GPT-4o & Claude 3.5 Sonnet credits) |
| **Mapbox / Leaflet JS** | Frontend spatial map rendering and parcel highlight visualization. | Open-source frontend library |

---

## 8. Two-to-Three-Week Project Plan

```
  Days 1-3          Days 4-7          Days 8-11         Days 12-14        Days 15-17        Days 18-19        Days 20-21
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  SETUP &    │   │ PLANNING &  │   │ MULTIMODAL  │   │   TRUST &   │   │   PRODUCT   │   │ BENCHMARK & │   │ HARDENING & │
│ FOUNDATIONS │──>│   ROUTING   │──>│ EXECUTION   │──>│  RECOVERY   │──>│ INTEGRATION │──>│ EVALUATION  │──>│ DEMO FREEZE │
└─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
```

| Days | Milestone | Deliverable |
| :--- | :--- | :--- |
| **1–3** | Architecture & Foundations | Finalize PostgreSQL/PostGIS schema, API wrappers, Qwen2.5-VL model container, project skeleton. |
| **4–7** | Planning & Routing | Integrate Task Graph Compiler, Capability Registry, Scored Router, and fallback templates. |
| **8–11** | Multimodal Execution | Integrate PaddleOCR, PostGIS spatial queries, RAG advisory retrieval, and in-memory Evidence Graph DAG. |
| **12–14** | Trust & Recovery Engine | Build Trust Engine ($FTS$), calibration scaler, bounded escalation, and abstention handlers. |
| **15–17** | Product Integration & UI | Connect React frontend with spatial Leaflet map, live DAG trace, evidence graph panel, and route telemetry. |
| **18–19** | Evaluation & Benchmarking | Run comparative benchmark (FARMSYNC vs. Pure GPT-4o vs. Static Routing), test unseen queries & failure injection. |
| **20–21** | Demo Freeze & Documentation | Code cleanup, deployment verification, reproducible demo recording, final technical documentation. |

**Final Deliverables**: Working web application, live orchestrator trace, cost/latency telemetry dashboard, evidence graph inspector, baseline benchmark report.

---

## 9. Team and Responsibilities

| Member | Registration ID / Role | Primary Responsibility |
| :--- | :--- | :--- |
| **Safi A (Lead)** | **TCPC-2026-00071**<br>AI & Orchestration Lead | Task Graph Compiler, Capability Registry, Verified-Utility Router, API integration, project leadership & team coordination. |
| **Mohamed asfaq S** | **TCPC-2026-00071**<br>AI Trust & Verification Lead | Trust Score ($FTS$) formulation, min-max calibration scaler, deterministic verification rules, bounded recovery manager, baseline evaluation suite. |
| **Sooraj TS** | **TCPC-2026-00071**<br>GeoAI, Full-Stack & UI Lead | PostgreSQL/PostGIS spatial engine setup, PaddleOCR & RAG pipeline, React + Leaflet interactive UI, execution trace, evidence graph visualization. |

---

## 10. Feasibility, Risks and Success

### Risk Mitigation Strategy

| Risk Factor | Mitigation Approach |
| :--- | :--- |
| **LLM Task Compiler Malformed DAG** | Closed JSON task schema + automatic fallback to pre-validated linear workflow template. |
| **Trust Score Calibration Data Shortage** | Min-max feature scaling calibrated on initial 20-sample validation subset; equal-weighted fallback ($w_i = 1/6$) when $N < 10$. |
| **Open-Weight VLM Latency / Hosting** | Host Qwen2.5-VL-7B via vLLM with quantized weights; fallback to GPT-4o-mini if local GPU credit unavailable. |
| **Scripted Happy Path Perception** | Test pipeline on deliberate low-confidence field photos, conflicting owner names, and unseen land acquisition queries. |
| **Unbounded Recursive Agent Loops** | Strictly cap prototype recovery to 1 alternate route before entering explicit `ABSTAIN_HUMAN_REVIEW` state. |

### Success Criteria
The FARMSYNC prototype will demonstrate success when:
1. A multimodal request is compiled into a structured task graph and executed across heterogeneous models and tools.
2. Routine vision perception is economically handled by open-weight models, while complex tasks escalate to proprietary VLMs.
3. Spatial operations (distance, containment, area) are computed deterministically via PostGIS without LLM hallucination.
4. Claims are backed by a transparent Evidence Graph DAG linked to source documents and databases.
5. Injected failures or missing evidence trigger bounded escalation or explicit abstention rather than forced predictions.
6. The system demonstrates >50% cost reduction over pure GPT-4o baselines on benchmark evaluation queries.
