import os
import json
from dotenv import load_dotenv
load_dotenv()
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from farmsync.orchestrator import FarmSyncOrchestrator
from farmsync.ai.engine import AIAssistantEngine
from farmsync.spatial.amazon_location import AmazonLocationServiceEngine

app = FastAPI(title="FARMSYNC Enterprise Platform", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core engines
orchestrator = FarmSyncOrchestrator()
ai_engine = AIAssistantEngine(orchestrator=orchestrator)
location_engine = orchestrator.location_engine

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
IMAGES_DIR = os.path.join(BASE_DIR, "data", "FAI_Product_Challange", "TASK_4", "Images", "images")
GEO_DIR = os.path.join(BASE_DIR, "data", "FAI_Product_Challange", "TASK_2", "Geospatial_Layer")

# In-memory cache for fast GeoJSON streaming
CACHED_PARCELS_GEOJSON = None
CACHED_ROADS_GEOJSON = None

STATUS_MAP = {
    "384": {"status": "Verified", "badge": "success", "date": "Oct 10, 2026", "crop": "Coconut", "owner": "Ramesh Kumar S/o Sundaram"},
    "381": {"status": "Verified", "badge": "success", "date": "Oct 09, 2026", "crop": "Rice (Paddy)", "owner": "Muthuvel P S/o Perumal"},
    "176": {"status": "Discrepancy", "badge": "error", "date": "Oct 08, 2026", "crop": "Rice (Paddy)", "owner": "Kandasamy V (Extent Mismatch)"},
    "382": {"status": "Escalated", "badge": "warning", "date": "Oct 08, 2026", "crop": "Banana", "owner": "Arumugam K S/o Krishnan"},
    "387": {"status": "Verified", "badge": "success", "date": "Oct 07, 2026", "crop": "Sugarcane", "owner": "Murugan S"},
    "174": {"status": "Verified", "badge": "success", "date": "Oct 06, 2026", "crop": "Maize", "owner": "Subramanian T"},
    "388": {"status": "Verified", "badge": "success", "date": "Oct 06, 2026", "crop": "Coconut", "owner": "Velmurugan P"},
    "175": {"status": "Verified", "badge": "success", "date": "Oct 05, 2026", "crop": "Rice (Paddy)", "owner": "Ponnusamy M"},
    "385": {"status": "Verified", "badge": "success", "date": "Oct 05, 2026", "crop": "Cotton", "owner": "Marimuthu K"},
    "386": {"status": "Verified", "badge": "success", "date": "Oct 04, 2026", "crop": "Groundnut", "owner": "Ganesan R"},
}

class OrchestrateRequest(BaseModel):
    query: str
    survey_no: Optional[str] = None
    document_path: Optional[str] = None
    force_escalate: Optional[bool] = False
    simulate_conflict: Optional[bool] = False
    simulate_ood: Optional[bool] = False

class AIQueryRequest(BaseModel):
    query: str
    survey_no: Optional[str] = None
    document_path: Optional[str] = None
    force_escalate: Optional[bool] = False
    simulate_conflict: Optional[bool] = False

class AWSSettingsRequest(BaseModel):
    access_key_id: str
    secret_access_key: str
    session_token: Optional[str] = None
    region: Optional[str] = "ap-south-1"

class RouteRequest(BaseModel):
    survey_no: str
    origin_lat: Optional[float] = None
    origin_lon: Optional[float] = None

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>FARMSYNC UI Initializing...</h1>"

@app.get("/api/parcels")
async def get_parcels():
    """Returns list of all parcels with summary statistics for the master list."""
    surveys = orchestrator.spatial.list_surveys()
    results = []

    for s in surveys:
        p = orchestrator.spatial.get_parcel(s)
        if p:
            meta = STATUS_MAP.get(s, {
                "status": "Verified", 
                "badge": "success", 
                "date": "Oct 02, 2026", 
                "crop": "Agricultural Land",
                "owner": f"Landholder (Survey {s})"
            })
            results.append({
                "survey_no": s,
                "name": f"Survey {s} - Block {p.get('block_id', '1')}",
                "village": p["village"],
                "district": p["district"],
                "area_acres": p["area_acres"],
                "status": meta["status"],
                "badge": meta["badge"],
                "date": meta["date"],
                "crop": meta["crop"],
                "owner": meta["owner"],
                "centroid": p["centroid"]
            })
    return {"total_parcels": len(surveys), "parcels": results}

@app.get("/api/parcel/{survey_no}")
async def get_parcel_detail(survey_no: str):
    """Returns full parcel spatial audit and geometry GeoJSON."""
    p = orchestrator.spatial.get_parcel(survey_no)
    if not p:
        raise HTTPException(status_code=404, detail="Parcel not found")
    constraints = orchestrator.spatial.check_constraints(survey_no)
    return {
        "parcel": p,
        "constraints": constraints
    }

@app.get("/api/geojson/all-parcels")
async def get_all_parcels_geojson():
    """Returns the full 396-parcel Cadastral Map layer enriched with audit metadata."""
    global CACHED_PARCELS_GEOJSON
    if CACHED_PARCELS_GEOJSON:
        return CACHED_PARCELS_GEOJSON

    cad_path = os.path.join(GEO_DIR, "Park_Cadastral_Map.geojson")
    if not os.path.exists(cad_path):
        raise HTTPException(status_code=404, detail="Cadastral map file not found")

    with open(cad_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Enrich each feature's properties with computed area, status, and crop
    for feat in data.get("features", []):
        props = feat.get("properties", {})
        s_no = str(props.get("survey_no", ""))
        p_info = orchestrator.spatial.get_parcel(s_no)
        meta = STATUS_MAP.get(s_no, {
            "status": "Verified",
            "badge": "success",
            "crop": "Agricultural Field",
            "owner": f"Landholder (Survey {s_no})"
        })
        
        area = p_info["area_acres"] if p_info else round(props.get("area", 0) / 4046.86, 2)
        props["area_acres"] = area
        props["status"] = meta["status"]
        props["badge"] = meta["badge"]
        props["crop"] = meta["crop"]
        props["owner"] = meta["owner"]

    CACHED_PARCELS_GEOJSON = data
    return CACHED_PARCELS_GEOJSON

@app.get("/api/geojson/roads")
async def get_roads_geojson():
    """Returns the local road network GeoJSON for Keelathattaparai."""
    global CACHED_ROADS_GEOJSON
    if CACHED_ROADS_GEOJSON:
        return CACHED_ROADS_GEOJSON

    roads_path = os.path.join(GEO_DIR, "Basic_GIS_Layers", "Local_Roads.geojson")
    if os.path.exists(roads_path):
        with open(roads_path, "r", encoding="utf-8") as f:
            CACHED_ROADS_GEOJSON = json.load(f)
            return CACHED_ROADS_GEOJSON
    return {"type": "FeatureCollection", "features": []}

@app.get("/api/geojson/waterbodies")
@app.get("/api/waterbodies")
async def get_waterbodies():
    """Returns GeoJSON of waterbodies for map overlay."""
    w_path = os.path.join(GEO_DIR, "Basic_GIS_Layers", "Waterbodies.geojson")
    if os.path.exists(w_path):
        with open(w_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"type": "FeatureCollection", "features": []}

@app.post("/api/ai/query")
async def run_ai_query(req: AIQueryRequest):
    """Executes natural language AI query with Bedrock or Enterprise Reasoner."""
    try:
        res = ai_engine.process_query(
            query=req.query,
            survey_no=req.survey_no,
            document_path=req.document_path,
            force_escalate=req.force_escalate or False,
            simulate_conflict=req.simulate_conflict or False
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents/list")
async def list_available_documents():
    """Lists official government land acquisition documents available for real extraction."""
    docs_dir = os.path.join(GEO_DIR.replace("Geospatial_Layer", "Land_documents"))
    categorized = {}
    if os.path.exists(docs_dir):
        for root, dirs, files in os.walk(docs_dir):
            for f in files:
                if f.lower().endswith(".pdf"):
                    rel = os.path.relpath(os.path.join(root, f), docs_dir)
                    cat = os.path.dirname(rel) or "General"
                    categorized.setdefault(cat, []).append({
                        "filename": f,
                        "relative_path": rel,
                        "size_bytes": os.path.getsize(os.path.join(root, f))
                    })
    return {"total_categories": len(categorized), "documents": categorized}

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Uploads a real PDF land document for extraction and analysis."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    upload_dir = os.path.join(GEO_DIR.replace("Geospatial_Layer", "Land_documents"), "Uploads")
    os.makedirs(upload_dir, exist_ok=True)
    target_path = os.path.join(upload_dir, file.filename)
    
    content = await file.read()
    with open(target_path, "wb") as f:
        f.write(content)
        
    return {
        "status": "UPLOAD_SUCCESS",
        "filename": file.filename,
        "saved_path": os.path.relpath(target_path, os.path.dirname(upload_dir)),
        "size_bytes": len(content)
    }

@app.post("/api/settings/aws")
async def update_aws_settings(req: AWSSettingsRequest):
    """Configures AWS Bedrock credentials dynamically from the UI."""
    status = ai_engine.configure_aws(
        access_key_id=req.access_key_id,
        secret_access_key=req.secret_access_key,
        session_token=req.session_token,
        region=req.region or "ap-south-1"
    )
    location_engine.configure_aws(
        access_key_id=req.access_key_id,
        secret_access_key=req.secret_access_key,
        session_token=req.session_token,
        region=req.region or "ap-south-1"
    )
    return status

@app.get("/api/settings/aws/status")
async def get_aws_settings_status():
    """Returns Bedrock readiness and connection status."""
    return ai_engine.get_status()

@app.get("/api/location/status")
async def get_location_status():
    """Returns Amazon Location Service connectivity and configuration."""
    return location_engine.get_status()

@app.get("/api/location/reverse-geocode/{survey_no}")
async def get_reverse_geocode(survey_no: str):
    """Reverse geocodes parcel centroid using Amazon Location Service."""
    p = orchestrator.spatial.get_parcel(survey_no)
    if not p:
        raise HTTPException(status_code=404, detail="Parcel not found")
    lat = p["centroid"]["latitude"]
    lon = p["centroid"]["longitude"]
    return location_engine.reverse_geocode(latitude=lat, longitude=lon, survey_no=survey_no)

@app.post("/api/location/route")
async def get_agri_route(req: RouteRequest):
    """Calculates ag-logistics route from depot to target parcel."""
    try:
        return location_engine.calculate_agri_route(
            survey_no=req.survey_no,
            origin_lat=req.origin_lat,
            origin_lon=req.origin_lon
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/location/geofence/{survey_no}")
async def get_geofence_status(survey_no: str):
    """Evaluates cadastral geofence buffer compliance."""
    return location_engine.evaluate_cadastral_geofence(survey_no)

@app.post("/api/orchestrate")
async def run_orchestration(req: OrchestrateRequest):
    """Executes full agentic orchestration workflow without fabrication."""
    effective_query = req.query
    if req.survey_no and f"Survey {req.survey_no}" not in effective_query and f"Survey Number {req.survey_no}" not in effective_query:
        effective_query = f"Analyze Survey Number {req.survey_no} in Keelathattaparai village: {req.query}"

    res = orchestrator.execute_request(
        query=effective_query,
        document_path=req.document_path,
        survey_no=req.survey_no,
        force_escalate_vision=req.force_escalate,
        simulate_conflict=req.simulate_conflict,
        simulate_unsupported_crop=req.simulate_ood
    )
    return res

@app.get("/api/image/{filename}")
async def get_image(filename: str):
    """Serves real field crop photo. Strictly refuses to return unrelated fallback photos."""
    if not filename or filename.lower() in ["none", "null", "undefined", "default"]:
        raise HTTPException(status_code=404, detail="No field photo on record for parcel")

    img_path = os.path.join(IMAGES_DIR, filename)
    if os.path.exists(img_path):
        return FileResponse(img_path, media_type="image/jpeg")

    raise HTTPException(status_code=404, detail=f"Field photo '{filename}' not found on disk")

@app.get("/api/knowledge/status")
async def get_knowledge_status():
    """Returns Agronomy RAG FAISS vector index status and metrics."""
    return orchestrator.knowledge.get_status()

@app.get("/api/status")
async def get_system_status():
    ai_status = ai_engine.get_status()
    k_status = orchestrator.knowledge.get_status()
    return {
        "status": "ONLINE",
        "aws_region": ai_status["region"],
        "bedrock_model": ai_status["active_model"],
        "bedrock_ready": ai_status["bedrock_client_ready"],
        "s3_bucket": "fai-tce-team26-data",
        "dynamodb_table": "fai-tce-team26-telemetry",
        "total_cadastral_parcels": len(orchestrator.spatial.list_surveys()),
        "total_indexed_field_photos": len(orchestrator.vision.image_registry),
        "rag_knowledge_engine": k_status.get("rag_engine"),
        "faiss_indexed_documents": k_status.get("total_indexed_documents", 0),
        "faiss_total_vectors": k_status.get("faiss_total_vectors", 0)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("farmsync.server:app", host="0.0.0.0", port=8000, reload=False)
