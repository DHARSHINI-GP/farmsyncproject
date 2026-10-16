# FARMSYNC: Evidence-Driven Adaptive AI Orchestration for Geospatial Intelligence
## Production Implementation Proposal & System Specification

**FarmwiseAI Campus Product Challenge · Task 1 Final Submission**  
**Registration ID**: TCPC-2026-00071  
**Team**: PRIME (Team 26) · Thiagarajar College of Engineering  
**Team Members**: Safi A (Lead), Mohamed Asfaq S, Sooraj TS  
**Live Platform**: [http://localhost:8000](http://localhost:8000) (FastAPI Enterprise UI) · [http://localhost:8501](http://localhost:8501) (Streamlit Benchmarking)  
**GitHub Repository**: [https://github.com/safi-prog/farmsync](https://github.com/safi-prog/farmsync)  
**AWS Production Account**: `9271-6111-4491` · **Active Role**: `FAI-TCE-Team26-Builder-Location` · **Region**: `ap-south-1` (Mumbai)  

---

> **Core Thesis**: FARMSYNC treats AI orchestration as a **verified decision problem**, not merely a model-selection problem. The system compiles multimodal geospatial requests into typed task graphs, routes each subtask using **Expected Verified Utility**, enforces **deterministic-first verification** (GeoPandas/Shapely GIS geometry & Amazon Location Service), executes live foundation reasoning via **AWS Bedrock**, constructs an **In-Memory Evidence Graph DAG**, and evaluates claim validity through a **Model-Agnostic Trust Score ($FTS$)** before producing a source-traceable answer.

---

## 1. Executive Summary & Production Shift

While preliminary conceptual proposals discussed abstract models (GPT-4o, Claude 3.5 Sonnet) on hypothetical villages, the **actual implemented system** is fully deployed, grounded, and verified against **real challenge datasets** and **live AWS cloud infrastructure in Mumbai (`ap-south-1`)**:

1. **AWS Bedrock Foundation Model Integration**: Integrated `mistral.ministral-3-3b-instruct` natively in Mumbai (`ap-south-1`) for sub-300ms multimodal agronomic reasoning, legal claim analysis, and structured audit synthesis under IAM Role `FAI-TCE-Team26-Builder-Location`.
2. **Amazon Location Service Integration**: Provisioned and live-tested `FARMSYNC_PlaceIndex` (Reverse Geocoding: Survey 384 centroid to `Keelathattapparai, Thoothukudi`) and `FARMSYNC_RouteCalculator` (Ag-Logistics: 10.71 km / 22.1 min transit from Vagaikulam TNAU Agricultural Supply Depot & Substation to parcel gate).
3. **Real Cadastral Ground Truth**: Ingested and rendered **396 real cadastral parcels** (`Park_Cadastral_Map.geojson`), **233 local road segments** (`Local_Roads.geojson`), waterbody protection layers (`Waterbodies.geojson`), and electrical substations for Keelathattapparai village, Thoothukudi, Tamil Nadu.
4. **Benchmark Survey 384**: Comprehensive vertical-slice verification on Survey Number 384 (10.35 acres claimed vs. 10.349 acres GeoPandas/Shapely GIS UTM 44N exact geometry; Section 7(2) Award Patta 176/1 PDF OCR extraction; healthy coconut plantation; ICAR-CPCRI TB 98 split fertilizer advisory).
5. **Dual-Interface Production Stack**: High-performance FastAPI backend with modern Glassmorphism Leaflet GIS interface on port 8000 and Streamlit Benchmark Telemetry Suite on port 8501.

---

## 2. System Architecture & Information Flow

```
                                  USER MULTIMODAL REQUEST
                 [Text Query + Scanned Patta PDF + Field Ground Photo + GIS Layers]
                                             │
                                             ▼
                                  ┌─────────────────────┐
                                  │ TASK GRAPH COMPILER │
                                  │ (Typed 7-Subtask DAG│
                                  └──────────┬──────────┘
                                             │
                                             ▼
                                  ┌─────────────────────┐
                                  │ CAPABILITY REGISTRY │
                                  │ Models, Tools & Lat.│
                                  └──────────┬──────────┘
                                             │
                                             ▼
                                  ┌─────────────────────┐
                                  │VERIFIED-UTILITY ROUTER
                                  │ Maximize Post-Verif.│
                                  └──────────┬──────────┘
                                             │
               ┌─────────────────────────────┼─────────────────────────────┐
               ▼                             ▼                             ▼
       AWS BEDROCK LLM               OPEN-WEIGHT VLM               DETERMINISTIC TOOLS
  mistral.ministral-3-3b-instruct     Qwen2.5-VL / ResNet-50       • GeoPandas/Shapely GIS (UTM 44N)
  (ap-south-1, 274ms latency)        (First-Pass Perception)       • Amazon Location Service:
  • Multimodal Reasoning             • Crop: Coconut                 - PlaceIndex (Reverse Geocoding)
  • Legal vs Cadastral Synthesis     • Stage: Full Growth            - RouteCalculator (Ag-Logistics)
  • ICAR Agronomic Advisory          • Health: Healthy             • PaddleOCR / PyMuPDF (Patta 176/1)
               │                             │                             │
               └─────────────────────────────┼─────────────────────────────┘
                                             ▼
                                  ┌─────────────────────┐
                                  │ IN-MEMORY EVIDENCE  │
                                  │      GRAPH DAG      │
                                  │ Claim ➔ Source Link │
                                  └──────────┬──────────┘
                                             │
                                             ▼
                                  ┌─────────────────────┐
                                  │    TRUST ENGINE     │
                                  │ Computes Score FTS  │
                                  └──────────┬──────────┘
                                             │
                     ┌───────────────────────┼───────────────────────┐
                     ▼                       ▼                       ▼
                  ACCEPT                  ESCALATE                 ABSTAIN
               (FTS ≥ 0.85)         (0.60 ≤ FTS < 0.85)          (FTS < 0.60)
                     │                       │                       │
                     │                       ▼                       ▼
                     │                 Alternate Model          Human Review
                     │                (Claude 3.5 Sonnet)       Flag Discrepancy
                     └───────────────────────┬───────────────────────┘
                                             ▼
                                   VERIFIED RESULT OBJECT
                         Interactive Map · Route Polyline · Telemetry
```

---

## 3. Mathematical Formulations

### 3.1 Verified-Utility Routing Objective

FARMSYNC rejects the naive assumption that routing should simply pick the highest-parameter LLM. Instead, it solves an optimization problem over available execution routes:

$$\text{RouteScore}(m, t) = \alpha \cdot \mathbb{E}[\text{Quality}(m, t)] - \beta \cdot \text{Cost}(m) - \gamma \cdot \text{Latency}(m) - \delta \cdot \text{Risk}(m, t) + \eta \cdot \Delta \text{VerifGain}$$

* $\mathbb{E}[\text{Quality}(m, t)]$: Expected task completion accuracy based on empirical calibration.
* $\text{Cost}(m)$: Cost in USD per invocation ($0.00015 for Bedrock Mistral 3B vs. $0.015 for GPT-4o).
* $\text{Latency}(m)$: Execution duration in seconds (274ms for Bedrock Mumbai vs. 2500ms for external multi-hop APIs).
* $\text{Risk}(m, t)$: Probability of schema violation or hallucinated entity.
* $\Delta \text{VerifGain}$: Expected increase in verifiable confidence when using tool-augmented execution.

### 3.2 Model-Agnostic Trust Score ($FTS$)

Vendor-reported confidence metrics (such as softmax probabilities or logprobs) are uncalibrated and non-comparable across heterogeneous open-weight and proprietary models. FARMSYNC computes trust exclusively from **independently observable signals**:

$$FTS = w_1 \cdot C_{\text{cal}} + w_2 \cdot E_{\text{cov}} + w_3 \cdot S_{\text{cons}} + w_4 \cdot D_{\text{val}} + w_5 \cdot O_{\text{val}} - w_6 \cdot P_{\text{conf}}$$

$$\text{Subject to: } \sum_{i=1}^{5} w_i = 1.0, \quad w_i \ge 0, \quad P_{\text{conf}} \in [0, 1]$$

| Factor | Symbol | Empirical Weight ($w_i$) | Live Benchmark Value (Survey 384) | Concrete Observable Evidence |
| :--- | :---: | :---: | :---: | :--- |
| **Historical Calibration** | $C_{\text{cal}}$ | 0.15 | 0.92 | Vision model empirical accuracy on coconut palm classification. |
| **Evidence Coverage** | $E_{\text{cov}}$ | 0.25 | 1.00 | Claim backed by 3 independent modalities (OCR, DB, GIS). |
| **Source Consistency** | $S_{\text{cons}}$ | 0.25 | 0.95 | Gazette owner name matches Cadastral registry attribute. |
| **Deterministic Validation** | $D_{\text{val}}$ | 0.25 | 0.98 | GeoPandas/Shapely GIS geometric area delta $< 0.1\%$ ($10.349$ vs. $10.350$ ac). |
| **Output Validity** | $O_{\text{val}}$ | 0.10 | 1.00 | 100% adherence to typed JSON Schema constraints. |
| **Conflict Penalty** | $P_{\text{conf}}$ | -0.20 | 0.00 | Zero spatial overlap conflict or boundary violation. |
| **Total Composite Score** | **$FTS$** | — | **0.971** *(exact: 0.9705)* | **VERIFIED_ACCEPTED** ($FTS \ge 0.85$) |

#### Step-by-Step Mathematical Calculation (Survey 384):
$$\begin{aligned}
FTS &= w_1 \cdot C_{\text{cal}} + w_2 \cdot E_{\text{cov}} + w_3 \cdot S_{\text{cons}} + w_4 \cdot D_{\text{val}} + w_5 \cdot O_{\text{val}} - w_6 \cdot P_{\text{conf}} \\
&= (0.15 \times 0.92) + (0.25 \times 1.00) + (0.25 \times 0.95) + (0.25 \times 0.98) + (0.10 \times 1.00) - (0.20 \times 0.00) \\
&= 0.1380 + 0.2500 + 0.2375 + 0.2450 + 0.1000 - 0.0000 \\
&= \mathbf{0.9705} \quad (\approx \mathbf{0.971} \text{ in 3-decimal engine output, } \mathbf{0.97} \text{ in 2-decimal breakdowns})
\end{aligned}$$

> **Audit Note on Formula Calibration**:
> Applying the calibrated weights ($0.15, 0.25, 0.25, 0.25, 0.10$) to the empirical signals for Survey 384 with zero conflict penalty produces strictly **0.9705** ($\ge 0.85 \implies \text{ACCEPT}$). An earlier preliminary draft included an illustrative $0.942$ placeholder (derived from a hypothetical $0.1425$ conflict penalty); the audited production codebase (`farmsync/trust/trust_score.py`) computes $P_{\text{conf}} = 0.00$ when all 3 independent evidence modalities agree, yielding the exact reproducible score of **0.9705**.

---

## 4. Implemented Cloud Infrastructure & Native AWS Integrations

### 4.1 AWS Production Environment
* **Account ID**: `9271-6111-4491`
* **Region**: `ap-south-1` (Mumbai, India)
* **Authenticated IAM Role**: `FAI-TCE-Team26-Builder-Location`
* **Session Profile**: STS Assumed Role with native Bedrock and Location Service policies.

### 4.2 Amazon Location Service Integration
FARMSYNC implements full native integration with Amazon Location Service via Boto3:

```python
# farmsync/spatial/amazon_location.py
import boto3

location_client = boto3.client('location', region_name='ap-south-1')
```

1. **Place Index (`FARMSYNC_PlaceIndex`)**:
   - `ARN`: `arn:aws:geo:ap-south-1:927161114491:place-index/FARMSYNC_PlaceIndex`
   - **Live Reverse Geocoding (`search_place_index_for_position`)**:
     Translates parcel centroid `[78.026997, 8.780888]` directly into:
     > `"Keelathattapparai, Thoothukudi, Tamil Nadu, IND"`
2. **Route Calculator (`FARMSYNC_RouteCalculator`)**:
   - `ARN`: `arn:aws:geo:ap-south-1:927161114491:route-calculator/FARMSYNC_RouteCalculator`
   - **Live Agricultural Logistics Routing (`calculate_route`)**:
     Calculates real-world road network transit distance and drive duration between the regional agricultural depot and the parcel:
     - **Origin**: Vagaikulam TNAU Agricultural Supply Depot & Substation (`8.752486°N, 77.992336°E`)
     - **Destination**: Survey 384 Centroid (`8.780888°N, 78.026997°E`)
     - **Calculated Distance**: **10.71 km**
     - **Calculated Transit Duration**: **22.1 minutes**
     - **Visualization**: Polyline geometry streamed via REST API and drawn as interactive route on the Leaflet map canvas.
3. **Cadastral Geofencing (`FARMSYNC_GeofenceCollection`)**:
   - Evaluates environmental buffer compliance against waterbody protection corridors (`Waterbodies.geojson`) to prevent agrochemical runoff violations.

### 4.3 AWS Bedrock Foundation Model Integration
FARMSYNC uses AWS Bedrock in `ap-south-1` (Mumbai) for foundational reasoning:
* **Model ID**: `mistral.ministral-3-3b-instruct`
* **Inference Endpoint**: `bedrock-runtime.ap-south-1.amazonaws.com`
* **Invocation Pattern**: `converse` API with structured system prompt and strict agronomic temperature ($T = 0.2$).
* **Performance Profile**: **274 ms average response latency**, zero outbound data egress outside India, and complete independence from foreign commercial endpoints.
* **Live Audit Synthesis**:
  1. *Cadastral & Legal Extent Verification*: Confirms 10.349 ac calculated vs 10.35 ac claimed.
  2. *Crop Perception & Health Diagnostic*: Confirms healthy full-growth coconut plantation.
  3. *Agronomic Advisory Formulation*: Prescribes ICAR-CPCRI Technical Bulletin 98 compliant fertilizer regimen (1.3 kg Urea + 2.0 kg Single Superphosphate + 2.0 kg Muriate of Potash per palm per year).

---

## 5. Real Dataset Grounding & Benchmark Scenarios

### 5.1 Dataset Specifications (Keelathattapparai Village, Thoothukudi)
Unlike simulated benchmarks, FARMSYNC is evaluated directly on real challenge artifacts:

| Layer / File | Format | Features | Ground Truth Details |
| :--- | :---: | :---: | :--- |
| `Park_Cadastral_Map.geojson` | Vector Polygon | **396 Parcels** | Complete cadastral land parcels with survey IDs and legal bounds. |
| `Local_Roads.geojson` | Vector LineString | **233 Roads** | Rural road network used for access analysis and delivery routing. |
| `Waterbodies.geojson` | Vector Polygon | **18 Waterbodies** | Tanks and channels used for 50m environmental buffer compliance. |
| `SubStations.geojson` | Vector Point | **12 Substations** | Infrastructure points including Vagaikulam regional hub. |
| `_176_1___F_.pdf` | Scanned Document | 3 Pages | Tamil Nadu Land Acquisition Section 7(2) Award Gazette notice. |
| Field Ground Photos | JPEG Imagery | 3,400+ Photos | Real field-level crop photographs across development stages. |

### 5.2 Primary Benchmark Query (Survey 384 Vertical Slice)
> *"Using the supplied Land Acquisition Award notice and field photography for Keelathattapparai village, identify Survey Number 384, verify its exact cadastral parcel geometry and registered land extent, predict crop classification and health condition from ground imagery, compute road logistics from Vagaikulam TNAU Agricultural Supply Depot via Amazon Location Service, perform environmental waterbody proximity buffer checks, and synthesize an ICAR-compliant agronomic audit using AWS Bedrock."*

---

## 6. Deterministic-First Grounded Execution

FARMSYNC adheres to the principle that **language models must never perform geometric, spatial, or arithmetic calculations** that deterministic engines can compute with mathematical certainty:

| Task Type | Handled By | Why Deterministic Tooling is Enforced |
| :--- | :--- | :--- |
| **Parcel Area Calculation** | GeoPandas / Shapely (`UTM 44N`) | Exact spherical polygon projection; prevents area estimation hallucinations. |
| **Waterbody Buffer Check** | GeoPandas / Shapely (50m Buffer) | Legal boundary violation verification requires exact spatial metric math. |
| **Logistics Routing** | Amazon Location Service (`calculate_route`) | Real road topology, one-way constraints, and speed profiles. |
| **Geographic Reverse Geocoding** | Amazon Location Service (`search_place_index`) | Authoritative administrative hierarchy lookup. |
| **Document Text Extraction** | PaddleOCR + PyMuPDF | Exact string parsing of revenue survey records and gazette tables. |
| **Advisory Retrieval** | FAISS + ICAR / TNAU Manuals | Exact cited guideline retrieval from approved agronomy texts. |

---

## 7. In-Memory Evidence Graph DAG & Output Schema

### 7.1 Directed Acyclic Evidence Structure
To maintain absolute provenance without the latency and deployment overhead of external graph databases (e.g. Neo4j), FARMSYNC constructs an **in-memory JSON DAG** passed across execution states:

```
[Survey 384 (Keelathattapparai)]
       │
       ├── EXTRACTED_FROM ──► Patta Award Document: _176_1___F_.pdf (Block 9, Award 7/2)
       │                        └─ Claimed Area: 10.350 Acres
       │
       ├── GEOMETRICALLY_GROUNDED_IN ──► Cadastral Polygon (Shapely): Park_Cadastral_Map.geojson
       │                                  ├─ Computed Area: 10.349 Acres (UTM 44N)
       │                                  ├─ Area Delta: -0.0097% (Fully Verified)
       │                                  └─ Centroid: [78.026997°E, 8.780888°N]
       │
       ├── GEOCODED_BY ──► Amazon Location Service PlaceIndex (FARMSYNC_PlaceIndex)
       │                     └─ Address: Keelathattapparai, Thoothukudi, Tamil Nadu, IND
       │
       ├── ACCESSIBLE_VIA ──► Amazon Location Service RouteCalculator (FARMSYNC_RouteCalculator)
       │                        ├─ Origin: Vagaikulam TNAU Agricultural Supply Depot
       │                        ├─ Distance: 10.71 km (Real Road Network)
       │                        └─ Travel Time: 22.1 mins
       │
       ├── VISUALLY_CLASSIFIED_BY ──► Vision Classifier (Qwen2.5-VL / ResNet-50)
       │                                ├─ Crop: Coconut (Confidence: 0.96)
       │                                ├─ Stage: Full Growth Stage
       │                                └─ Health: Healthy (Zero Deficiency)
       │
       └── AUDITED_BY ──► AWS Bedrock (mistral.ministral-3-3b-instruct)
                            ├─ Reference: ICAR-CPCRI Technical Bulletin 98
                            └─ Fertilizer Regimen: 1.3 kg Urea + 2.0 kg SSP + 2.0 kg MOP / palm / yr
```

### 7.2 Implemented `VerifiedResultObject` Schema
```json
{
  "survey_number": "384",
  "village": "Keelathattapparai",
  "district": "Thoothukudi",
  "claimed_extent_acres": 10.35,
  "gis_extent_acres": 10.349,
  "extent_discrepancy_pct": 0.0097,
  "extent_status": "FULLY_VERIFIED",
  "reverse_geocoding": {
    "provider": "Amazon Location Service (FARMSYNC_PlaceIndex)",
    "formatted_address": "Keelathattapparai, Thoothukudi, Tamil Nadu, IND",
    "coordinates": [78.026997, 8.780888]
  },
  "logistics_route": {
    "provider": "Amazon Location Service (FARMSYNC_RouteCalculator)",
    "origin": "Vagaikulam TNAU Agricultural Supply Depot & Substation",
    "distance_km": 10.71,
    "duration_minutes": 22.1,
    "route_geojson_available": true
  },
  "crop_intelligence": {
    "crop_type": "Coconut",
    "growth_stage": "Full Growth Stage",
    "health_status": "Healthy",
    "visual_confidence": 0.96
  },
  "environmental_compliance": {
    "waterbody_buffer_50m": "COMPLIANT",
    "buffer_conflict_detected": false
  },
  "trust_evaluation": {
    "model_reported_confidence": 0.96,
    "farmwise_trust_score_fts": 0.971,
    "verification_verdict": "VERIFIED_ACCEPTED"
  },
  "telemetry": {
    "primary_planner": "FARMSYNC Task Graph Compiler",
    "foundation_model": "mistral.ministral-3-3b-instruct (AWS Bedrock)",
    "execution_region": "ap-south-1",
    "latency_ms": 274,
    "estimated_cost_usd": 0.00042
  }
}
```

---

## 8. Interactive Production Interfaces

### 8.1 Modern Enterprise Glassmorphism UI (`http://localhost:8000`)
Built on FastAPI, Leaflet GIS, and modern Glassmorphism CSS:
* **Interactive GIS Canvas**: Renders all 396 cadastral parcels with dynamic fill colors based on verification state (🟢 Verified, 🟡 Caution, 🔴 Discrepancy).
* **Live Road & Water Overlays**: Toggles 233 local roads and waterbody buffer zones.
* **Instant Parcel Inspection Modal**: Clicking any parcel flies the camera to the boundary, fetches legal records, and displays live attributes.
* **Amazon Location Route Polyline**: Dynamically renders the 10.71 km supply run route from Vagaikulam Depot directly onto the map.
* **Bedrock Live Audit Generator**: Runs real-time foundation model inference with a single click, streaming structured agronomic findings.

### 8.2 Streamlit Benchmark & Telemetry Dashboard (`http://localhost:8501`)
* **3-Way Comparative Benchmark**: Real-time evaluation of **FARMSYNC vs. Simulated Premium-Only vs. Simulated Static Routing**.
* **Failure Injection Suite**: Demonstrates bounded escalation when image noise is introduced, and explicit abstention when document records conflict.
* **FTS Score Breakdown**: Visual radar and bar charts decomposing the 6 observable trust signals.

---

## 9. Baseline Benchmark & Simulated Architectural Comparison

To evaluate how adaptive orchestration compares against un-orchestrated paradigms, FARMSYNC was evaluated across the 50-query cadastral benchmark (`data/benchmark_results.json` executed via `farmsync/benchmark/evaluator.py`).

> [!IMPORTANT]
> **Notice on Competitor Baseline Simulation**:
> The competitor metrics reported below reflect **simulated architectural baselines**, not live evaluations against third-party commercial APIs (such as OpenAI GPT-4o or Anthropic Claude 3.5 Sonnet).
> * **FARMSYNC (Adaptive Orchestration)** is evaluated **live query-by-query** on the actual local open-weight vision model (MobileNetV3/CropNet), deterministic GeoPandas/Shapely GIS engine, and FTS trust verification logic.
> * **Simulated Premium-Only Baseline** models the structural behavior of prompt-only frontier VLMs: it runs FarmSync's internal teacher vision backbone with forced escalation, assigns prompt-based spatial outcomes by query category (modeling the absence of metric polygon GIS tools through simulated estimates, such as an unverified 15m waterbody buffer distance), applies a token pricing assumption of $0.01250/query, and introduces synthetic network latency offsets (1,450ms base + jitter).
> * **Simulated Static Pipeline Baseline** models an un-orchestrated pipeline: it runs the student vision model without teacher escalation, extracts documents without multi-source FTS conflict reconciliation, lacks metric buffer tools, and unconditionally accepts all queries under a fixed cost assumption ($0.00085/query).
> These comparisons are intended as **architectural projections** illustrating the theoretical failure modes of un-orchestrated systems rather than measured empirical competitor benchmarks under identical live execution conditions.

### 9.1 Overall System Comparison (Measured FARMSYNC vs. Simulated Baselines)

| Metric | Simulated Premium Baseline (Prompt-Only Frontier VLM) | Simulated Static Baseline (Fixed Routing Pipeline) | FARMSYNC Adaptive Orchestration (Measured Live Run) | Advantage vs. Simulated Premium |
| :--- | :---: | :---: | :---: | :---: |
| **Verified Accuracy** | 46.0% *(23/50)* | 44.0% *(22/50)* | **100.0%** *(50/50)* | **+54.0% Accuracy Gain** |
| **Average Cost per Query** | $0.01250 *(assumed)* | $0.00085 *(assumed)* | **$0.00120** *(measured)* | **90.4% Cost Reduction** |
| **Average Latency** | 1,632 ms *(synthetic)* | 176 ms *(measured)* | **236 ms** *(local)* / **311 ms** *(audit)* | **85.5% Latency Reduction** |
| **Spatial Hallucination Rate** | 44.0% *(22/50)* | 32.0% *(16/50)* | **0.0%** *(0/50)* | **100% Hallucination Elimination** |
| **Cost Savings vs Premium** | 0.0% | 93.2% | **90.4%** | **Optimal Verified Utility** |
| **Bounded Recovery Guarantee** | No *(unbounded prompt loops)* | No *(static fail on noise)* | **Yes** *(Bounded 1-hop recovery / abstain)* | **Guaranteed Safe Termination** |

### 9.2 Category Breakdown: Measured FARMSYNC vs. Simulated Baselines (50 Queries)

| Category | Queries | FARMSYNC Accuracy (Measured) | Simulated Premium Accuracy | Simulated Static Accuracy | Avg Latency (ms) | Avg Cost ($) | Simulated Unorchestrated Failure Modes |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Confident Grounded** | 22 | **100.0%** | 68.2% | 100.0% | 170 ms | $0.00120 | Simulated prompt parsing variance in pure VLMs. |
| **Perception Escalation** | 8 | **100.0%** | 100.0% | 0.0% | 245 ms | $0.00120 | Static pipeline lacks escalation on blurred/noisy images. |
| **Buffer & Spatial Access** | 6 | **100.0%** | 0.0% | 0.0% | 228 ms | $0.00120 | Both baselines lack UTM 44N metric polygon math. |
| **Document Discrepancy** | 8 | **100.0%** | 0.0% | 0.0% | 247 ms | $0.00120 | Premium exhibits sycophancy; Static lacks conflict gating. |
| **Unsupported & Abstain** | 6 | **100.0%** | 0.0% | 0.0% | 458 ms | $0.00120 | Baselines hallucinate guesses rather than cleanly abstaining. |
| **Total / Overall** | **50** | **100.0%** | **46.0%** | **44.0%** | **236 ms** | **$0.00120** | **Deterministic grounding eliminates spatial hallucinations.** |

---

## 10. Live Verification Matrix

All components have been executed live in the test environment and verified:

| Subsystem | Target Endpoint / AWS Resource | Verification Command / Method | Status | Live Observed Output |
| :--- | :--- | :--- | :---: | :--- |
| **AWS Authentication** | `sts.ap-south-1.amazonaws.com` | `sts.get_caller_identity()` | **PASS** | Role: `FAI-TCE-Team26-Builder-Location` (Acct: `927161114491`) |
| **Amazon Location** | `FARMSYNC_PlaceIndex` | `search_place_index_for_position()` | **PASS** | Centroid resolved to `Keelathattapparai, Thoothukudi` |
| **Amazon Location** | `FARMSYNC_RouteCalculator` | `calculate_route()` | **PASS** | `10.71 km`, `22.1 mins` from Vagaikulam Depot |
| **AWS Bedrock** | `mistral.ministral-3-3b-instruct` | `bedrock-runtime.converse()` | **PASS** | Complete agronomic audit in `274 ms` |
| **Cadastral GIS API** | `GET /api/geojson/all-parcels` | FastAPI HTTP Request | **PASS** | 396 GeoJSON parcel polygons delivered |
| **Local Road API** | `GET /api/geojson/roads` | FastAPI HTTP Request | **PASS** | 233 GeoJSON road LineStrings delivered |
| **Waterbody API** | `GET /api/geojson/waterbodies` | FastAPI HTTP Request | **PASS** | 18 GeoJSON waterbody polygons delivered |
| **Parcel Verification** | `GET /api/verify-parcel/384` | FastAPI HTTP Request | **PASS** | Extent: 10.349 ac, $FTS = 0.971$ *(exact: 0.9705)*, Status: `VERIFIED_ACCEPTED` |
| **Git Repository** | `https://github.com/safi-prog/farmsync` | `git push -u origin main` | **PASS** | Commit `1e3b0201` live on branch `main` |

---

## 11. Conclusion & Submission Sign-Off

The implemented FARMSYNC system successfully fulfills every requirement of **Task 1: Multi-Model, Multimodal and Agentic AI System**:
* Genuine orchestration across heterogeneous open-weight and foundational models.
* Native production integration with **Amazon Location Service** and **AWS Bedrock** in `ap-south-1` Mumbai.
* Rigorous deterministic-first spatial computation eliminating LLM geometric hallucinations.
* Observable claim-to-source traceability via an in-memory Evidence Graph DAG and Model-Agnostic Trust Scoring ($FTS$).
* Fully deployable dual-interface platform running locally and version-controlled on GitHub.

**Submitted by Team PRIME (Team 26)**  
*Thiagarajar College of Engineering, Madurai*  
Safi A (Lead) · Mohamed Asfaq S · Sooraj TS
