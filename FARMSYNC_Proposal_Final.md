> **Historical proposal / submission draft.** This document includes superseded architecture and unverified cloud claims. The organizer access guide and [HACKATHON_READINESS.md](HACKATHON_READINESS.md) govern the current implementation and live acceptance status.

# FARMSYNC: Evidence-Driven Adaptive AI Orchestration for Geospatial Intelligence

**FarmwiseAI Campus Product Challenge · Task 1 Submission**  
**Selected Use Case**: Parcel Evidence & Advisory Intelligence  

> **Core Thesis**: FARMSYNC treats AI orchestration as a verified decision problem, not merely a model-selection problem. The system selects an execution route using expected verified utility, then proves whether the resulting claims are sufficiently supported before answering.

---

## 1. Executive Summary

FARMSYNC is a reusable, evidence-driven AI orchestration layer for complex multimodal geospatial requests. It accepts natural-language requests together with documents, images, and structured data; converts the request into a typed task graph; selects models and deterministic tools through a capability-aware routing policy; executes the workflow while maintaining shared state; constructs an evidence graph; and verifies important results before producing a final answer.

The central design decision is that the system will not rely on vendor-reported model confidence as a common trust signal. Instead, FARMSYNC computes a model-agnostic, task-specific **Trust Score ($FTS$)** from independently observable signals such as evidence coverage, source consistency, deterministic validation, output validity, historical calibration, and conflict indicators.

The router also avoids using a large language model as the primary routing decision-maker. The planner determines what must be done; a lightweight scored/learned router determines which model or tool should do it. Routing optimizes **expected verified utility**: the expected quality of a result after verification, balanced against cost, latency, and failure risk.

**Why this matters for FarmwiseAI**: Task 1 explicitly asks for genuine orchestration across models and tools, verification, fallback, shared state, structured outputs, and route/latency/cost comparison. FARMSYNC makes these requirements the visible product rather than background implementation details.

---

## 2. Proposal at a Glance

| Item | Specification |
| :--- | :--- |
| **Challenge** | Task 1 — Multi-Model, Multimodal and Agentic AI System |
| **Project Name** | **FARMSYNC** — Evidence-Driven Adaptive AI Orchestration for Geospatial Intelligence |
| **Primary Use Case** | Parcel Evidence & Advisory Intelligence |
| **Primary Differentiator** | Verified-Utility Routing + Task-Specific Trust Scoring ($FTS$) + In-Memory Evidence Graph |
| **Models Candidate Set** | **Proprietary A**: GPT-4o / Claude 3.5 Sonnet (Planning & Complex Reasoning)<br>**Proprietary B**: Gemini 1.5 Pro / GPT-4o-mini (Independent Verification)<br>**Open-Weight**: Qwen2.5-VL-7B / Llama-3.2-Vision (Low-Cost First-Pass Perception) |
| **Deterministic Tools** | Document/OCR (PaddleOCR), Structured DB (PostgreSQL), GIS Engine (PostGIS/GeoPandas), RAG Retrieval, Python Execution |
| **Output Specification** | Verified parcel intelligence with interactive map, evidence graph, confidence/trust breakdown, execution trace, and route telemetry |
| **Development Window** | 2–3 weeks after shortlisting |

---

## 3. Data, Compute, and Model Access Requirements

To develop and demonstrate the working prototype within the 2–3 week stage 2 sprint, FARMSYNC will require access to the following resources:

1. **Cadastral & Parcel Geospatial Data**: Sample vector cadastral parcel maps (GeoJSON/Shapefile format) with survey boundaries, administrative hierarchy (District $\rightarrow$ Taluk $\rightarrow$ Village), and land attributes for 1–2 sample villages.
2. **Land Records & Field Imagery**: A sample set of anonymized land documents (scanned Patta/acquisition notices in PDF format) and matching ground field photos with metadata (timestamp, GPS coordinates).
3. **Agronomy & Advisory Document Corpus**: Approved agricultural advisory documents, crop growth stage handbooks, and fertilizer/pest management recommendation manuals for RAG indexing.
4. **Spatial Database Infrastructure**: PostgreSQL instance with PostGIS extension enabled for deterministic geometric and distance calculations.
5. **Cloud Compute for Open-Weight Model**: AWS GPU compute credits (e.g., g5.xlarge with NVIDIA A10G or equivalent) to host and serve the open-weight vision-language model (e.g., Qwen2.5-VL-7B) via vLLM/Ollama.
6. **API Credits for Proprietary Models**: Cloud API access/credits for two commercial models (e.g., OpenAI GPT-4o and Anthropic Claude 3.5 Sonnet or Google Gemini 1.5 Pro).

---

## 4. Understanding of the Problem

Complex FarmwiseAI workflows are not single-model questions. A single user request may involve document understanding, entity resolution, database retrieval, geospatial computation, image interpretation, knowledge retrieval, and final reasoning. The central systems problem is therefore deciding which capabilities should be used, in which order, under what evidence requirements, and how the system should respond when a result is uncertain or contradictory.

* **Single-Model Inefficiency**: Using one premium model for every subtask can be unnecessarily expensive and slow.
* **Lack of Coherence**: Calling several models independently without orchestration does not create a coherent workflow.
* **Non-Deterministic Vulnerability**: LLMs should not be trusted with deterministic spatial and numeric operations that can be computed exactly.
* **Confidence Incomparability**: Model-reported confidence is not directly comparable across heterogeneous proprietary and open-weight models. While model-reported confidence fields are ingested as one non-binding feature into the calibration component, FARMSYNC relies strictly on the task-specific Model-Agnostic Trust Score ($FTS$) derived from observable multi-source evidence and deterministic verification to govern escalation and acceptance.
* **Evidence-Based Verification**: Verification must examine the relationship between a claim and its independent evidence, not merely ask another model to agree.
* **Graceful Abstention**: In difficult cases, a reliable system must be able to abstain rather than manufacture a confident answer.

---

## 5. Product Concept

### 5.1 What FARMSYNC Builds

1. **Interpret Request**: Interpret the user request and identify required inputs, outputs, and constraints.
2. **Task Graph Compilation**: Compile the request into a typed execution graph with task dependencies. *Fallback*: If the LLM Task Graph Compiler returns an invalid or malformed DAG, the system automatically falls back to a pre-validated linear baseline workflow template for the domain.
3. **Capability Matching**: Match each task against a capability registry of models, tools, and data sources.
4. **Verified-Utility Routing**: Choose an execution route using expected verified utility, cost, latency, and risk.
5. **Shared State Execution**: Execute heterogeneous model and tool calls while preserving shared state.
6. **Evidence Graph Construction**: Construct an in-memory evidence graph connecting claims to source documents, database records, computations, and model outputs.
7. **Trust Engine Evaluation**: Run task-specific verification checks and compute a model-agnostic Trust Score ($FTS$).
8. **Bounded Recovery**: Accept, escalate once to an alternate route, or abstain/handoff when evidence is insufficient.
9. **Traceable Presentation**: Present a source-traceable final answer together with route, cost, latency, and verification telemetry.

---

### 5.2 Demonstration Use Case (Primary): Parcel Evidence & Advisory Intelligence

The prototype will demonstrate a multimodal parcel workflow using a realistic scenario:

> **Example Query 1 (Primary)**:  
> *"Using the supplied land document and field photograph for Devapura village, identify Survey Number 144/3B, verify its parcel boundary and registered owner, predict the crop type and growth stage from the field image, retrieve the applicable fertilizer advisory, perform relevant spatial proximity checks against restricted waterbody zones, and return a source-traceable verified recommendation."*

```
Request → Task Graph → Capability Matching → Verified-Utility Router
        → Model/Tool Execution → Evidence Graph → Trust Engine
        → [ ACCEPT / ESCALATE / ABSTAIN ] → Verified Result
```

---

### 5.3 Unseen Request Demonstration (Genericity Proof)

To demonstrate that FARMSYNC is a generic, reusable control plane rather than a hard-coded single-query pipeline, the system will execute completely different requests dynamically:

> **Example Query 2 (Unseen Land Document Discrepancy Query)**:  
> *"Read the uploaded land acquisition notice 'Acquisition_2024_04.pdf', extract all survey numbers, subdivisions, and listed land extents. Cross-check each record against the PostGIS cadastral parcel layer and registry database, flag any extent discrepancies exceeding 5% or ownership mismatches, and present the discrepancies on a synchronized map and report."*

When Query 2 is submitted, the **Task Graph Compiler** dynamically generates a Land Document OCR $\rightarrow$ Entity Extraction $\rightarrow$ Database Join $\rightarrow$ PostGIS Geometric Intersection $\rightarrow$ Discrepancy Flagging DAG, routing OCR and extraction to specialized lightweight models and geometric math to PostGIS, **without modifying a single line of orchestration code**.

---

## 6. Core Technical Thesis: Verified Utility Routing

FARMSYNC is designed around a deliberate position: the routing problem is not *"Which model is smartest?"* but *"Which execution route is most likely to produce a sufficiently verified result for this specific task at acceptable cost and latency?"*

This leads to an explicit objective function:

$$\text{Expected Verified Utility} = \text{Expected Verified Quality} - \lambda \cdot \text{Cost} - \mu \cdot \text{Latency} - \rho \cdot \text{Failure Risk}$$

The system can therefore prefer a smaller model (e.g., Qwen2.5-VL) when it is likely to achieve adequate verified quality, while reserving premium models (e.g., GPT-4o / Claude 3.5 Sonnet) for complex planning or cases where the expected marginal benefit of escalation justifies additional cost and latency.

---

## 7. Model-Agnostic Trust Score ($FTS$)

FARMSYNC will not treat the confidence field returned by different models as directly comparable. Instead, it estimates trust from observable evidence about the result:

$$FTS = w_1 \cdot \text{Calibration} + w_2 \cdot \text{EvidenceCoverage} + w_3 \cdot \text{SourceConsistency} + w_4 \cdot \text{DeterministicValidation} + w_5 \cdot \text{OutputValidity} - w_6 \cdot \text{ConflictPenalty}$$

| Signal | Meaning | Concrete Example |
| :--- | :--- | :--- |
| **Calibration** | Historical reliability of the model/task pair on a validation set | Vision model accuracy for supported crop classes |
| **Evidence Coverage** | How much of the claim is directly supported by retrieved evidence | Owner claim supported by document + database |
| **Source Consistency** | Agreement between independent sources | Document owner matches registry owner |
| **Deterministic Validation** | Exact computational or rule-based checks | GIS distance, area difference, polygon containment |
| **Output Validity** | Schema, type, and structural constraint validity | Required fields present; valid geometry/numbers |
| **Conflict / OOD Penalty** | Contradictory evidence or unsupported input indicators | Two sources disagree or image outside supported distribution |

> **Design Principle**: Trust is not treated as a permanent property of a model. It is a property of a specific result in a specific verification context.  
> *Note on Hyperparameters*: To avoid manual heuristic bias, weights $w_1 \dots w_6$ will be normalized using a min-max feature scaler calibrated on an initial 20-sample validation subset provided during Stage 2, defaulting to equal weights ($w_i = 1/6$) when initial calibration sample size $N < 10$.

---

## 8. Router Design & Separation of Responsibilities

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
                            │   TOOL EXECUTION    │
                            │ GIS / SQL / Python  │
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

### 8.1 Component Responsibilities

| Component | Responsibility | What it does NOT do |
| :--- | :--- | :--- |
| **Planner / Task Graph Compiler** | Determines what must happen and task dependencies | Does not select the final model provider for every step |
| **Capability Registry** | Describes available model/tool capabilities & operating specs | Does not execute tasks |
| **Router** | Selects the route that maximizes expected verified utility | Does not generate the final answer |
| **Executor** | Runs models/tools and records outputs | Does not silently overwrite evidence |
| **Trust Engine** | Evaluates whether a result is sufficiently supported | Does not blindly accept a model confidence field |
| **Recovery Manager** | Performs bounded escalation or abstention | Does not enter an unbounded autonomous loop |

---

### 8.2 Initial Scored Router Objective

$$\text{RouteScore}(\text{model}, \text{task}) = \alpha \cdot \text{ExpectedQuality} - \beta \cdot \text{ExpectedCost} - \gamma \cdot \text{ExpectedLatency} - \delta \cdot \text{FailureRisk} + \eta \cdot \text{ExpectedVerificationGain}$$

---

## 9. Bounded Escalation and Abstention

FARMSYNC intentionally avoids open-ended recursive replanning in the prototype. The recovery policy is bounded and testable:

```
RESULT
  │
  ▼
Trust Engine
  ├── ACCEPT → continue
  ├── ESCALATE → one alternate model/tool route → verify again
  └── ABSTAIN / REVIEW → insufficient verified evidence
```

* **Escalate** when task-specific trust falls below the acceptance threshold.
* **Escalate** when critical evidence sources conflict.
* **Escalate** when required evidence is missing but another approved route can obtain it.
* **Abstain** when the alternate route still fails validation or evidence remains contradictory.
* **Never force** a prediction solely because the application must return an answer.

---

## 10. In-Memory Evidence Graph & Concrete Output Schema

The prototype represents provenance as an in-memory Directed Acyclic Graph (DAG) JSON structure rather than a flat source list, eliminating external graph database deployment overhead while preserving strict relationship tracing.

```
Survey 144/3B
 ├─ extracted-from → Acquisition_Notice_04.pdf
 ├─ matches → Parcel P94102
 │   ├─ owner → Ramesh Kumar
 │   ├─ area → 3.85 acres
 │   └─ geometry → polygon (PostGIS verified)
 ├─ associated-with → Field_Photo_Devapura_144.jpg
 │   └─ crop → Cotton (Stage: Flowering)
 └─ advisory-supported-by → Advisory_Cotton_Pest_08.pdf
```

### Concrete Output Schema (`VerifiedResultObject`)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "VerifiedResultObject",
  "type": "object",
  "properties": {
    "claim_id": { "type": "string", "example": "CLM-2026-DEV-144" },
    "survey_number": { "type": "string", "example": "144/3B" },
    "village": { "type": "string", "example": "Devapura" },
    "extracted_attributes": {
      "registered_owner": "Ramesh Kumar",
      "gis_area_acres": 3.85,
      "predicted_crop": "Cotton",
      "growth_stage": "Flowering"
    },
    "source_evidence": [
      {
        "source_type": "DOCUMENT_OCR",
        "source_ref": "Acquisition_Notice_04.pdf#Page2",
        "extracted_value": "Ramesh Kumar",
        "confidence": 0.91
      },
      {
        "source_type": "DATABASE_REGISTRY",
        "source_ref": "Land_Registry_DB.parcels",
        "extracted_value": "Ramesh Kumar",
        "confidence": 1.0
      }
    ],
    "deterministic_checks": {
      "postgis_containment_valid": true,
      "extent_mismatch_percentage": 0.0,
      "waterbody_buffer_conflict": false
    },
    "trust_metrics": {
      "model_reported_confidence": 0.84,
      "task_trust_score_fts": 0.95,
      "verification_status": "VERIFIED_ACCEPTED"
    },
    "routing_telemetry": {
      "primary_model": "Qwen2.5-VL-7B-Instruct",
      "escalation_model": "Claude-3.5-Sonnet",
      "was_escalated": true,
      "total_latency_ms": 1120,
      "estimated_cost_usd": 0.0038
    }
  }
}
```

---

## 11. Deterministic-First Verification

Where a result can be computed or checked exactly, FARMSYNC will use deterministic tools instead of asking a language model to reason about the same fact.

| Problem | Preferred Mechanism | Technical Reason |
| :--- | :--- | :--- |
| **Distance between parcel & road/waterbody** | GIS / PostGIS | Deterministic spatial computation (`ST_Distance`) |
| **Parcel intersection / containment** | GIS / PostGIS | Exact geometric operation (`ST_Contains`) |
| **Area difference calculation** | Python / Database | Exact numeric comparison (`abs(doc_area - gis_area)`) |
| **Survey record lookup** | Structured Database | Direct SQL key lookup |
| **Schema validation** | Programmatic JSON Schema | Prevents malformed structured output |
| **Semantic image interpretation** | Open VLM $\rightarrow$ Proprietary VLM | Requires visual perception |
| **Advisory synthesis** | RAG + LLM | Requires source-grounded text synthesis |

---

## 12. Multi-Model Architecture

| Model Class | Candidate Models | Primary Role | Fallback / Escalation Role |
| :--- | :--- | :--- | :--- |
| **Proprietary Model A** | OpenAI GPT-4o / Claude 3.5 Sonnet | Complex planning, task graph compilation, synthesis | Primary strong route for high-complexity tasks |
| **Proprietary Model B** | Google Gemini 1.5 Pro / GPT-4o-mini | Independent verification & complex multimodal escalation | Alternate route when evidence/confidence is insufficient |
| **Open-Weight Model** | Qwen2.5-VL-7B / Llama-3.2-Vision | Low-cost first-pass perception, OCR, crop classification | Routine route; replaced when trust score $FTS < 0.70$ |

*Note*: Exact commercial model versions will be finalized after FarmwiseAI confirms approved credits; the architecture remains provider-agnostic.

---

## 13. Prototype Experience (UI Dashboard)

The application will make orchestration visible rather than hiding it behind a simple chat box:

| Panel | What the Judge Sees |
| :--- | :--- |
| **Request Panel** | Original multimodal question, uploaded documents, field photos, and spatial layer inputs |
| **Execution Graph Panel** | Live planner-created DAG tasks and their real-time execution status |
| **Verified Result Panel** | Final parcel, owner, crop/stage, and advisory findings |
| **Evidence Graph Panel** | Interactive claim-to-source relationships and verification state |
| **Interactive Map Panel** | Relevant parcel polygon, boundary highlights, and spatial context |
| **Route Telemetry Panel** | Selected model/tool per step, routing rationale, execution latency, and cost ($USD) |
| **Recovery State Panel** | Explicit escalation, fallback, or abstention status when triggered |

---

## 14. Baseline and Evaluation Design

To demonstrate that adaptive orchestration adds tangible value, the prototype will benchmark FARMSYNC against two baselines:

| Baseline | Definition | Purpose |
| :--- | :--- | :--- |
| **Premium-Only** | Use the strongest approved proprietary model for every single AI step | Measures potential cost and latency savings |
| **Static Routing** | Fixed model choice by task type (no adaptive verification or escalation) | Measures value of adaptive routing and trust scoring |
| **FARMSYNC** | Verified-utility route + deterministic tools + Trust Engine ($FTS$) | Measures full proposed architecture |

---

## 15. Risks and Mitigation

| Risk | Mitigation |
| :--- | :--- |
| **Overengineering** | Implement one complete vertical slice first; keep the router, trust engine, and recovery policy bounded. |
| **Model/API Access Changes** | Provider-agnostic model adapter layer; final providers selected after approved access is known. |
| **DAG Compiler Failure** | Automatic fallback to pre-validated linear workflow templates if LLM outputs an invalid DAG. |
| **Trust Score Weight Calibration** | Min-max feature scaling initialized on a 20-sample validation subset; equal-weighted fallback if $N < 10$. |
| **Demo Scripted Happy Path** | Include an unseen query plus deliberate low-confidence, conflict, and tool-failure test cases. |
| **Unbounded Agent Loops** | Strictly limit prototype recovery to one alternate route before entering explicit abstention/human review. |

---

## 16. Two-to-Three-Week Prototype Plan

```
  Days 1-3          Days 4-7          Days 8-11         Days 12-14        Days 15-17        Days 18-19        Days 20-21
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│    DATA &   │   │  PLANNING & │   │ MULTIMODAL  │   │   TRUST &   │   │   PRODUCT   │   │ EVALUATION  │   │ HARDENING & │
│ FOUNDATIONS │──>│   ROUTING   │──>│  EXECUTION  │──>│  RECOVERY   │──>│ INTEGRATION │──>│ & BENCHMARK │──>│    DEMO     │
└─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
```

| Period | Milestone | Deliverable |
| :--- | :--- | :--- |
| **Days 1–3** | Data + Foundations | Data/schema setup, model/tool access, PostGIS DB initialization, project skeleton |
| **Days 4–7** | Planning + Routing | Task graph compiler, capability registry, scored router, model adapters |
| **Days 8–11** | Multimodal Execution | Document OCR, GIS, vision, and RAG integration; shared state; evidence graph DAG |
| **Days 12–14** | Trust + Recovery | Trust engine ($FTS$), validation rules, escalation, fallback, abstention logic |
| **Days 15–17** | Product Integration | Interactive map, verified result panel, execution trace UI, route telemetry |
| **Days 18–19** | Evaluation | Baseline comparison (FARMSYNC vs. Premium vs. Static), failure injection, unseen query test |
| **Days 20–21** | Hardening + Demo | Optimization, deployment, UX polish, reproducible demo video, final docs |

---

## 17. Team Responsibilities

| Role | Primary Ownership |
| :--- | :--- |
| **AI / Orchestration Lead** | Planner, task graph compiler, capability registry, router, model adapters |
| **AI / Trust Lead** | Trust Score ($FTS$), calibration, verification rules, baseline evaluation suite |
| **Geo / Data Lead** | PostGIS database setup, parcel data ingestion, spatial queries, evidence relationships |
| **Product / Full-Stack Lead** | Frontend UI, interactive map, execution trace, evidence graph, and telemetry panels |
| **Integration / QA Lead** | End-to-end workflows, failure injection, test query suite, demo readiness |

---

## 18. Research and Design Grounding

The proposal is informed by current peer-reviewed work in model routing, tool-using agents, geospatial AI, and verification:

* **RouteLLM** (Zheng et al., 2024, arXiv:2406.18665): Routing large language models based on quality/cost trade-offs.
* **Self-Refine** (Madaan et al., 2023, arXiv:2303.17651): Iterative feedback/refinement as a general model improvement mechanism.
* **GeoGPT** (Zhang et al., 2023, arXiv:2307.07930): Natural-language-driven geospatial analysis and tool use.
* **Geospatial Agent Verification Frameworks** (e.g., GeoAnalystBench, 2025; RouteLLM, 2024): Evaluation of geospatial agent workflow validity, spatial reasoning, and decision-theoretic control planes.

---

## Appendix A — Task 1 Requirement Coverage Checklist

| FarmwiseAI Requirement | FARMSYNC Implementation Response |
| :--- | :--- |
| **Planner / Orchestrator** | Task Graph Compiler with fallback linear workflow template |
| **2+ Proprietary Models** | Candidate: GPT-4o (Planning/Synthesis) & Claude 3.5 Sonnet / Gemini 1.5 Pro (Verification) |
| **1 Open-Weight / Smaller Model** | Candidate: Qwen2.5-VL-7B / Llama-3.2-Vision (Low-cost first-pass vision/OCR) |
| **Model Router** | Verified-Utility Router ($\text{Expected Quality} - \text{Cost} - \text{Latency} - \text{Risk}$) |
| **Task / Capability / Cost / Latency** | Capability Registry + Scored Route Telemetry |
| **Tool / Data Connectors** | OCR (PaddleOCR), Database (PostgreSQL), GIS (PostGIS), RAG, Python |
| **Structured Outputs** | Typed Task Graph, `VerifiedResultObject` JSON Schema |
| **Verifier / Critic** | Trust Engine ($FTS$) + Deterministic GIS / Rule Validation |
| **Fallback / Recovery** | Bounded alternate route escalation + explicit abstention state |
| **Shared State / Memory** | Execution state + In-memory Evidence Graph DAG |
| **Multimodal Inputs** | Text + Documents + Images + Structured Data + Spatial GIS Layers |
| **2+ Meaningful Tool Calls** | Planned across Document OCR, PostGIS spatial queries, RAG, Database joins |
| **Visible Route, Latency, Cost** | Live Telemetry & Execution Trace UI Panel |
| **Unseen Comparable Request** | Evaluated on Land Acquisition Discrepancy Query (Query 2) without code changes |
| **No Hard-Coded Answers** | Dynamic DAG compilation and capability-based routing |
