# FARMSYNC: Multimodal Geospatial AI Platform

<div align="center">

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![AWS Bedrock](https://img.shields.io/badge/AWS_Bedrock-ap--south--1-FF9900.svg?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/bedrock/)
[![Amazon Location](https://img.shields.io/badge/Amazon_Location-Place_&_Route-232F3E.svg?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/location/)
[![PostGIS UTM 44N](https://img.shields.io/badge/GIS-EPSG:32644-27AE60.svg)](https://epsg.io/32644)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**An Enterprise Multi-Model, Multimodal & Agentic AI System for Cadastral Land Verification, Ag-Logistics Routing, and Agronomic Intelligence**

*Developed for the FarmwiseAI Campus Product Challenge (Task 1)*  
**Team**: PRIME (`TCPC-2026-00071`) · **Institution**: Thiagarajar College of Engineering, Madurai

</div>

---

## 🌟 Key Features

- **🗺️ Interactive 396-Parcel Cadastral Vector GIS**:
  - Full vector polygon rendering of all 396 cadastral parcels in Keelathattaparai village, Thoothukudi.
  - Hover tooltips, click-to-focus inspection, and dynamic status styling (🟢 Verified, 🟡 Caution, 🔴 Discrepancy).
  - High-resolution satellite basemap toggle (Esri World Imagery) and 233 local road vectors.

- **📍 Amazon Location Service Integration (`ap-south-1` Mumbai)**:
  - **Reverse Geocoding (`FARMSYNC_PlaceIndex`)**: Translates parcel centroids into official Tamil Nadu administrative village addresses.
  - **Ag-Logistics Supply Route Calculator (`FARMSYNC_RouteCalculator`)**: Calculates transit paths, driving distances (**10.71 km**), and durations (**22.1 mins**) from Vagaikulam TNAU Supply Depot to farmer parcels, plotted on Leaflet.
  - **Cadastral Geofencing**: Real-time auditing against 50m environmental waterbody buffer protection zones.

- **🧠 Live AWS Bedrock Foundation Models**:
  - Live natural language reasoning via `mistral.ministral-3-3b-instruct` / Claude 3.5 in Mumbai.
  - Generates structured executive summaries, regulatory extent cross-checks, and fertilizer schedules.

- **📐 Deterministic PostGIS Zero-Hallucination Extent Verification**:
  - Computes exact metric parcel area in UTM Zone 44N (`EPSG:32644`).
  - Mathematically detects document mismatches without LLM spatial hallucinations.

- **🌾 Multimodal Vision Crop Classifier & Teacher Escalation**:
  - Ingests 3,422 field photos to classify crop species (`Coconut`, `Paddy`, `Maize`, `Banana`, `Sugarcane`) and growth stages.
  - Automatic escalation from lightweight student models to high-capacity reasoning models upon uncertainty.

- **🛡️ Model-Agnostic Trust Score (FTS)**:
  - Synthesizes 5 independent evidence signals into a single score:
    $$\text{FTS} = w_1 \cdot \text{Calibration} + w_2 \cdot \text{EvidenceCoverage} + w_3 \cdot \text{SourceConsistency} + w_4 \cdot \text{DeterministicVal} + w_5 \cdot \text{OutputValidity} - w_6 \cdot \text{ConflictPenalty}$$
  - Triggers Refuse-to-Invent abstentions upon evidence discrepancies.

- **📚 Cited Agronomic Package of Practices**:
  - Grounded in official TNAU Agritech & ICAR-CPCRI Technical Bulletins.

---

## 🏛️ System Architecture

```
                                USER REQUEST / NATURAL LANGUAGE PROMPT
                                                  │
                                                  ▼
                                       ┌─────────────────────┐
                                       │ TASK GRAPH COMPILER │
                                       └──────────┬──────────┘
                                                  │
                                                  ▼
                                       ┌─────────────────────┐
                                       │VERIFIED-UTILITY ROUTER│
                                       └──────────┬──────────┘
                                                  │
                     ┌────────────────────────────┼────────────────────────────┐
                     ▼                            ▼                            ▼
         [AWS Bedrock Foundation]      [Amazon Location Service]     [Deterministic PostGIS]
          Ministral 3B / Claude 3.5     Place Index & Routing         UTM 44N Area & Buffers
          (ap-south-1 Mumbai)           (ap-south-1 Mumbai)           (Zero Hallucination)
                     │                            │                            │
                     └────────────────────────────┼────────────────────────────┘
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
                     [ ACCEPT ]              [ ESCALATE ]            [ ABSTAIN ]
                  All evidence valid      Low vision conf. →      Discrepancy detected →
                                          Teacher verification    Regulatory Audit
```

---

## 🚀 Quick Start Guide

### 1. Clone the Repository
```bash
git clone https://github.com/safi-prog/farmsync.git
cd farmsync
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure AWS Credentials (Optional for Live Bedrock/Location)
Create a `.env` file in the root directory:
```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_SESSION_TOKEN=your_session_token # If using IAM Identity Center / SSO
AWS_DEFAULT_REGION=ap-south-1
BEDROCK_MODEL_ID=mistral.ministral-3-3b-instruct
AMAZON_LOCATION_INDEX=FARMSYNC_PlaceIndex
AMAZON_LOCATION_ROUTER=FARMSYNC_RouteCalculator
AMAZON_LOCATION_GEOFENCE=FARMSYNC_GeofenceCollection
```
*(Note: If AWS credentials are not set, the platform seamlessly runs with the built-in deterministic offline GIS and reasoning engine with 100% functionality).*

### 4. Run the Modern Platform (FastAPI UI)
```bash
python -m uvicorn farmsync.server:app --host 0.0.0.0 --port 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

### 5. Run the Streamlit Benchmark Dashboard
```bash
python -m streamlit run farmsync/ui/app.py --server.port 8501
```
Open **[http://localhost:8501](http://localhost:8501)** in your browser.

---

## 📂 Project Structure

```
farmsync/
├── farmsync/
│   ├── ai/
│   │   └── engine.py              # AWS Bedrock & Chain-of-Thought reasoning engine
│   ├── spatial/
│   │   ├── engine.py              # Deterministic PostGIS UTM 44N geometric engine
│   │   └── amazon_location.py     # Amazon Location Place Index & Route Calculator
│   ├── vision/
│   │   └── classifier.py          # Multimodal crop perception & student/teacher escalation
│   ├── documents/
│   │   └── extractor.py           # Document OCR & legal registry cross-referencing
│   ├── knowledge/
│   │   └── advisory.py            # TNAU/ICAR agronomic guidance & package of practices
│   ├── router/
│   │   ├── compiler.py            # Natural language Task Graph DAG compiler
│   │   └── router.py              # Verified-Utility capability-aware subtask router
│   ├── trust/
│   │   ├── trust_score.py         # Model-Agnostic Trust Score (FTS) engine
│   │   └── evidence_graph.py      # Directed Acyclic Graph (DAG) provenance builder
│   ├── static/
│   │   └── index.html             # Modern enterprise UI (Leaflet map + HUD + AI Copilot)
│   ├── ui/
│   │   └── app.py                 # Streamlit benchmark and evaluation dashboard
│   ├── orchestrator.py            # Master workflow coordination pipeline
│   └── server.py                  # FastAPI REST API backend (Port 8000)
├── data/                          # Cadastral GeoJSON layers, road vectors & crop photos
├── tests/                         # Automated unit and integration test suite
├── scripts/
│   └── setup_amazon_location.py  # Automation script for AWS Location Service setup
├── FARMSYNC_Final_Submission.md   # Final comprehensive technical proposal
├── FARMSYNC_Presentation_Deck.pptx# Executive presentation slide deck (8 widescreen slides)
├── requirements.txt               # Python package dependencies
├── .gitignore                     # Repository exclusion rules
└── README.md                      # Project documentation
```

---

## 🧪 Testing & Verification

Run automated test suite:
```bash
pytest tests/ -v
```

All spatial, vision, orchestrator, and AWS integration tests run with 100% pass rates.

---

## 👥 Team & Submission Information

- **Challenge**: FarmwiseAI Campus Product Challenge 2026 (Task 1)
- **Team**: PRIME (`Team-26`)
- **Submission ID**: `TCPC-2026-00071`
- **Institution**: Thiagarajar College of Engineering, Madurai, Tamil Nadu
- **Team Members**:
  - Mohammed Asfaq S (`mohamedasfaq@student.tce.edu`)
  - Safi A (`safi@student.tce.edu`)
  - Sooraj TS (`soorajts@student.tce.edu`)

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
