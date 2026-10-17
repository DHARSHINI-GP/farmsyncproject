import os
import re
import hmac
import json
import logging
import time
import uuid
import base64
import hashlib
import html
from dotenv import load_dotenv
load_dotenv()
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, UploadFile, File, Security, Depends, Request
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from farmsync.orchestrator import FarmSyncOrchestrator
from farmsync.ai.engine import AIAssistantEngine
from farmsync.spatial.amazon_location import AmazonLocationServiceEngine
from farmsync.runtime import Runtime
from farmsync.platform_api import install as install_platform
from farmsync.aws import check_approved_services, TEXT_MODEL, TEACHER_MODEL, EMBEDDING_MODEL, REGION

app = FastAPI(title="FARMSYNC Enterprise Platform", version="2.0.0")

# Security-hardened CORS configuration
raw_origins = os.getenv(
    "FARMSYNC_ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000,http://localhost:8501,http://127.0.0.1:8501"
)
if raw_origins.strip() == "*":
    ALLOWED_ORIGINS = ["*"]
    ALLOW_CREDENTIALS = False
else:
    ALLOWED_ORIGINS = [orig.strip() for orig in raw_origins.split(",") if orig.strip()]
    ALLOW_CREDENTIALS = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "Accept"],
)

# Authentication and Access Control Dependencies
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
HTTP_BEARER = HTTPBearer(auto_error=False)
MAX_UPLOAD_SIZE_BYTES = int(os.getenv("FARMSYNC_MAX_UPLOAD_SIZE", str(15 * 1024 * 1024))) # 15 MB default

def is_trusted_local_client(request: Request) -> bool:
    """Verifies whether incoming client request originates from local loopback or test runner."""
    client_host = request.client.host if request.client else ""
    return client_host in ("127.0.0.1", "::1", "localhost", "testclient")

async def verify_sensitive_endpoint_access(
    request: Request,
    api_key_header: Optional[str] = Security(API_KEY_HEADER),
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Security(HTTP_BEARER)
) -> bool:
    """
    Access control policy for sensitive endpoints (AWS credential management, document uploads).
    
    SECURITY ENFORCEMENT:
    1. If FARMSYNC_API_KEY is configured in the environment:
       - Every request (local or remote) MUST provide this key via 'X-API-Key'
         or 'Authorization: Bearer <key>'. Constant-time comparison prevents timing attacks.
    2. If FARMSYNC_API_KEY is NOT set in the environment:
       - Trusted local loopback (127.0.0.1, ::1, testclient) is permitted for local operation.
       - Any external network client is REJECTED with 401 Unauthorized before network exposure.
    """
    if getattr(request.state, "principal", None) or runtime.resolve_session(request):
        return True
    if runtime.production or runtime.store.user_count() > 0:
        raise HTTPException(401, "Sign in with an individual account")
    provided_key = api_key_header or (auth_credentials.credentials if auth_credentials else None)
    if not provided_key and "api-key" in request.headers:
        provided_key = request.headers.get("api-key")

    # Also inspect JSON body if provided for POST endpoints
    if not provided_key and request.headers.get("content-type", "").startswith("application/json"):
        try:
            body_bytes = await request.body()
            if body_bytes:
                body_json = json.loads(body_bytes)
                if isinstance(body_json, dict) and "api_key" in body_json:
                    provided_key = body_json.get("api_key")
        except Exception:
            pass

    configured_key = os.getenv("FARMSYNC_API_KEY", "").strip()

    if configured_key:
        if not isinstance(provided_key, str) or not hmac.compare_digest(provided_key.encode(), configured_key.encode()):
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: Invalid or missing API key for sensitive endpoint."
            )
        request.state.principal = {"id": "local-admin", "username": "local-admin", "role": "admin"}
        return True

    # If no FARMSYNC_API_KEY is configured in env:
    if is_trusted_local_client(request):
        request.state.principal = {"id": "local-admin", "username": "local-admin", "role": "admin"}
        return True

    raise HTTPException(
        status_code=401,
        detail="Unauthorized: Sensitive endpoint requires authentication when accessed beyond local loopback. Configure FARMSYNC_API_KEY to authorize network requests."
    )


@app.middleware("http")
async def protect_challenge_data(request: Request, call_next):
    request_id = uuid.uuid4().hex
    request.state.request_id = request_id
    started = time.monotonic()
    response = None
    origin = request.headers.get('origin')
    if request.url.path.startswith('/api/') and request.method not in {'GET','HEAD','OPTIONS'} and origin and origin not in ALLOWED_ORIGINS:
        response = JSONResponse(status_code=403, content={'detail':'Unapproved request origin'})
    # The organizer-provided datasets must not be exposed by unauthenticated APIs.
    if response is None and request.url.path.startswith("/api/") and request.method != "OPTIONS" and request.url.path not in {"/api/auth/login", "/api/auth/status"}:
        try:
            credentials = await HTTP_BEARER(request)
            await verify_sensitive_endpoint_access(request, request.headers.get("X-API-Key"), credentials)
            if request.url.path.startswith("/api/settings/aws") and request.method == "POST":
                runtime.admin(request)
        except HTTPException as exc:
            response = JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    if response is None:
        response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    logging.getLogger("farmsync.requests").info(json.dumps({"request_id": request_id, "method": request.method, "path": request.url.path, "status": response.status_code, "latency_ms": round((time.monotonic() - started) * 1000, 2)}))
    return response

def sanitize_upload_filename(filename: Optional[str]) -> str:
    """
    Sanitizes client-provided filename to prevent directory traversal and filesystem attacks.
    - Strips path components and directory traversal tokens ('..', '/', '\\').
    - Whitelists safe characters: alphanumeric, hyphens, underscores, dots, single spaces.
    - Strictly enforces .pdf extension.
    """
    if not filename or not isinstance(filename, str):
        raise HTTPException(status_code=400, detail="Missing or invalid filename.")

    # Normalize separators and extract basename only
    normalized = filename.replace("\\", "/")
    base = os.path.basename(normalized).strip()

    # Reject explicit null bytes
    if "\0" in base:
        raise HTTPException(status_code=400, detail="Invalid character in filename.")

    # Remove relative traversal tokens
    base = re.sub(r'\.\.+', '.', base)
    name, ext = os.path.splitext(base)

    if ext.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Whitelist stem characters
    clean_stem = re.sub(r'[^a-zA-Z0-9_\-\. ]', '_', name).strip('. ')
    if not clean_stem:
        clean_stem = "uploaded_document"

    clean_stem = clean_stem[:100].rstrip('. ')
    return f"{clean_stem}.pdf"

# Initialize core engines
orchestrator = FarmSyncOrchestrator()
ai_engine = AIAssistantEngine(orchestrator=orchestrator)
location_engine = orchestrator.location_engine
runtime = Runtime(orchestrator, ai_engine)
install_platform(app, runtime)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
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
# These are presentation fixtures, not persisted audits. Require an explicit opt-in.
if os.getenv("FARMSYNC_DEMO_MODE", "false").lower() != "true":
    STATUS_MAP = {}

class OrchestrateRequest(BaseModel):
    query: str = Field(min_length=1, max_length=8000)
    survey_no: Optional[str] = None
    parcel_id: Optional[str] = None
    image_filename: Optional[str] = None
    document_path: Optional[str] = None
    force_escalate: Optional[bool] = False
    simulate_conflict: Optional[bool] = False
    simulate_ood: Optional[bool] = False

class AIQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=8000)
    survey_no: Optional[str] = None
    parcel_id: Optional[str] = None
    image_filename: Optional[str] = None
    document_path: Optional[str] = None
    force_escalate: Optional[bool] = False
    simulate_conflict: Optional[bool] = False

class AWSSettingsRequest(BaseModel):
    access_key_id: str
    secret_access_key: str
    session_token: Optional[str] = None
    region: Optional[str] = "ap-south-1"
    api_key: Optional[str] = None
    model_id: Optional[str] = Field(default=None, min_length=1, max_length=256)

class RouteRequest(BaseModel):
    survey_no: str
    parcel_id: Optional[str] = None
    origin_lat: Optional[float] = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    origin_lon: Optional[float] = Field(default=None, ge=-180, le=180, allow_inf_nan=False)

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            source = f.read()
        scripts = re.findall(r"<script\b[^>]*>(.*?)</script>", source, flags=re.S)
        handlers = [html.unescape(v) for v in re.findall(r'\bon\w+="([^"]*)"', source)]
        hashes = {"'sha256-" + base64.b64encode(hashlib.sha256(v.encode()).digest()).decode() + "'" for v in scripts + handlers if v.strip()}
        policy = "default-src 'none'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; "
        policy += "script-src 'self' 'unsafe-hashes' " + " ".join(sorted(hashes)) + "; "
        policy += "style-src 'self' 'unsafe-inline'; font-src 'self'; connect-src 'self'; img-src 'self' data: blob: https://*.basemaps.cartocdn.com https://server.arcgisonline.com;"
        return HTMLResponse(source, headers={"Content-Security-Policy": policy, "X-Frame-Options": "DENY"})
    return "<h1>FARMSYNC UI Initializing...</h1>"

@app.get("/api/parcels")
async def get_parcels():
    """Returns list of all parcels with summary statistics for the master list."""
    surveys = orchestrator.spatial.list_surveys()
    results = []

    for _, row in orchestrator.spatial.gdf_parcels_wgs84.iterrows():
        s = str(row["survey_no_clean"])
        p = orchestrator.spatial.get_parcel(str(row["parcel_id"]))
        if p:
            if s in STATUS_MAP:
                meta = STATUS_MAP[s]
            else:
                ror = orchestrator.docs.revenue_registry.get(str(s))
                owner_name = ror.get("registered_owner") if ror else None
                meta = {
                    "status": "Not verified", 
                    "badge": "neutral", 
                    "date": "-", 
                    "crop": "Unclassified",
                    "owner": owner_name or f"Survey {s} (Unaudited)"
                }
            results.append({
                "survey_no": s,
                "parcel_id": p["parcel_id"],
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
    return {
        "total_parcels": len(results), "parcels": results,
        "distinct_survey_numbers": len(surveys),
        "ambiguous_survey_numbers": sum(orchestrator.spatial.get_parcel(s) is None for s in surveys)
    }

@app.get("/api/parcel/{survey_no:path}")
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
    for row_index, feat in enumerate(data.get("features", [])):
        props = feat.get("properties", {})
        s_no = str(props.get("survey_no", ""))
        p_info = orchestrator.spatial.get_parcel(s_no)
        if s_no in STATUS_MAP:
            meta = STATUS_MAP[s_no]
        else:
            ror = orchestrator.docs.revenue_registry.get(s_no)
            owner_name = ror.get("registered_owner") if ror else None
            meta = {
                "status": "Not verified",
                "badge": "neutral",
                "crop": "Unclassified",
                "owner": owner_name or f"Survey {s_no} (Unaudited)"
            }
        
        # Each map feature has its own polygon, even when a survey number repeats.
        geometry = orchestrator.spatial.gdf_parcels_utm.iloc[row_index].geometry
        area = round(float(geometry.area) / 4046.8564224, 3)
        props["identity_ambiguous"] = p_info is None
        props["parcel_id"] = str(orchestrator.spatial.gdf_parcels_wgs84.iloc[row_index]["parcel_id"])
        if p_info is None:
            meta = {"status": "Not verified", "badge": "neutral", "crop": "Unclassified", "owner": "Village/block identity required"}
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
def run_ai_query(req: AIQueryRequest, request: Request, _auth: bool = Depends(verify_sensitive_endpoint_access)):
    return runtime.analyze(runtime.user(request), req.model_dump())

@app.get("/api/documents/list")
async def list_available_documents(request: Request):
    """Lists official government land acquisition documents available for real extraction."""
    docs_dir = os.path.join(GEO_DIR.replace("Geospatial_Layer", "Land_documents"))
    categorized = {}
    if os.path.exists(docs_dir):
        for root, dirs, files in os.walk(docs_dir):
            dirs[:] = [d for d in dirs if d != "Uploads"]
            for f in files:
                if f.lower().endswith(".pdf"):
                    rel = os.path.relpath(os.path.join(root, f), docs_dir)
                    cat = os.path.dirname(rel) or "General"
                    categorized.setdefault(cat, []).append({
                        "filename": f,
                        "relative_path": rel,
                        "size_bytes": os.path.getsize(os.path.join(root, f))
                    })
    owned = runtime.store.assets(runtime.user(request)["id"], "pdf")
    if owned:
        categorized["My uploads"] = [{"filename": a["original_name"], "relative_path": "asset:" + a["id"], "size_bytes": 0} for a in owned]
    return {"total_categories": len(categorized), "documents": categorized}

@app.post("/api/documents/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    _auth: bool = Depends(verify_sensitive_endpoint_access)
):
    sanitize_upload_filename(file.filename)
    return await runtime.upload(request, file, "pdf", limit=MAX_UPLOAD_SIZE_BYTES)

@app.post("/api/settings/aws")
async def update_aws_settings(
    req: AWSSettingsRequest,
    request: Request,
    _auth: bool = Depends(verify_sensitive_endpoint_access)
):
    """Configures AWS Bedrock credentials dynamically with access control verification."""
    if os.getenv("FARMSYNC_ALLOW_RUNTIME_CREDENTIALS", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="AWS credentials are configured on the server through .env, SSO or its deployment role. Browser credential editing is disabled.")
    status = ai_engine.configure_aws(
        access_key_id=req.access_key_id,
        secret_access_key=req.secret_access_key,
        session_token=req.session_token,
        region=req.region or "ap-south-1",
        model_id=req.model_id
    )
    location_engine.configure_aws(
        access_key_id=req.access_key_id,
        secret_access_key=req.secret_access_key,
        session_token=req.session_token,
        region=req.region or "ap-south-1"
    )
    orchestrator.vision.configure_aws(
        req.access_key_id, req.secret_access_key, req.session_token,
        req.region or "ap-south-1"
    )
    return status

@app.get("/api/settings/aws/status")
async def get_aws_settings_status():
    """Returns Bedrock readiness and connection status."""
    return {
        **ai_engine.get_status(),
        "approved_text_models": [TEXT_MODEL, TEACHER_MODEL],
        "approved_embedding_model": EMBEDDING_MODEL,
        "credential_source": "SSO/profile or server environment/deployment role",
        "live_service_checks": getattr(app.state, "aws_checks", None),
    }


@app.post("/api/settings/aws/check")
def verify_approved_aws_services(_auth: bool = Depends(verify_sensitive_endpoint_access)):
    """Explicit live check of approved models only; no resource creation."""
    # Reload only AWS configuration after the operator refreshes a local session.
    from dotenv import dotenv_values
    allowed = {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_DEFAULT_REGION", "AWS_CA_BUNDLE", "AWS_PROFILE", "FARMSYNC_AWS_PROFILE", "BEDROCK_MODEL_ID", "BEDROCK_VISION_MODEL_ID"}
    for key, value in dotenv_values(os.path.join(BASE_DIR, ".env")).items():
        if key in allowed and value is not None:
            if value:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)
    ai_engine.region = os.getenv("AWS_DEFAULT_REGION", REGION)
    ai_engine.bedrock_model_id = os.getenv("BEDROCK_MODEL_ID", TEXT_MODEL)
    ai_engine._init_bedrock_client()
    orchestrator.vision.bedrock_model_id = os.getenv("BEDROCK_VISION_MODEL_ID", TEACHER_MODEL)
    orchestrator.vision._init_bedrock_client()
    result = check_approved_services()
    app.state.aws_checks = result
    text_check = result["checks"].get("text_3b", result["checks"].get("credentials", {}))
    ai_engine.last_bedrock_check = {"success": text_check.get("status") == "PASS", "error_code": text_check.get("error_code"), "checked_at_utc": result["checked_at_utc"]}
    return result

@app.get("/api/location/status")
async def get_location_status():
    """Returns Amazon Location Service connectivity and configuration."""
    return location_engine.get_status()

@app.get("/api/location/reverse-geocode/{survey_no:path}")
async def get_reverse_geocode(survey_no: str):
    """Reverse geocodes parcel centroid using Amazon Location Service."""
    p = orchestrator.spatial.get_parcel(survey_no)
    if not p:
        raise HTTPException(status_code=404, detail="Parcel not found")
    lat = p["centroid"]["latitude"]
    lon = p["centroid"]["longitude"]
    return location_engine.reverse_geocode(latitude=lat, longitude=lon, survey_no=survey_no)

@app.post("/api/location/route")
def get_agri_route(req: RouteRequest, _auth: bool = Depends(verify_sensitive_endpoint_access)):
    """Calculates ag-logistics route from depot to target parcel."""
    try:
        return location_engine.calculate_agri_route(
            survey_no=req.parcel_id or req.survey_no,
            origin_lat=req.origin_lat,
            origin_lon=req.origin_lon
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/location/geofence/{survey_no:path}")
async def get_geofence_status(survey_no: str):
    """Evaluates cadastral geofence buffer compliance."""
    return location_engine.evaluate_cadastral_geofence(survey_no)

@app.post("/api/orchestrate")
def run_orchestration(req: OrchestrateRequest, request: Request, _auth: bool = Depends(verify_sensitive_endpoint_access)):
    return runtime.analyze(runtime.user(request), req.model_dump(), ai=False)

@app.get("/api/image/{filename}")
async def get_image(filename: str, request: Request):
    """Serves real field crop photo. Strictly refuses to return unrelated fallback photos."""
    if not filename or filename.lower() in ["none", "null", "undefined", "default"]:
        raise HTTPException(status_code=404, detail="No field photo on record for parcel")

    if filename.startswith("asset:"):
        asset = runtime.store.asset(filename[6:], runtime.user(request)["id"])
        if not asset or asset["kind"] != "image":
            raise HTTPException(404, "Image not found")
        return FileResponse(asset["path"], media_type="image/jpeg")
    record = orchestrator.vision.image_registry.get(filename)
    if not record:
        raise HTTPException(status_code=404, detail="Image is not in the authorized photo library")
    img_path = record["filepath"]
    if os.path.exists(img_path):
        return FileResponse(img_path, media_type="image/jpeg")

    raise HTTPException(status_code=404, detail=f"Field photo '{filename}' not found on disk")


@app.get("/api/images")
def list_image_evidence(request: Request):
    images = [{"filename": f} for f in sorted(orchestrator.vision.image_registry) if not f.startswith("asset:")]
    images += [{"filename": "asset:" + a["id"], "label": a["original_name"]} for a in runtime.store.assets(runtime.user(request)["id"], "image")]
    return {"images": images}

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
        "s3_integrated": False,
        "dynamodb_integrated": False,
        "total_cadastral_parcels": len(orchestrator.spatial.gdf_parcels_wgs84),
        "distinct_survey_numbers": len(orchestrator.spatial.list_surveys()),
        "total_indexed_field_photos": len(orchestrator.vision.image_registry),
        "rag_knowledge_engine": k_status.get("rag_engine"),
        "faiss_indexed_documents": k_status.get("total_indexed_documents", 0),
        "faiss_total_vectors": k_status.get("faiss_total_vectors", 0)
    }

if __name__ == "__main__":
    import uvicorn
    # Default to secure local loopback (127.0.0.1). Set FARMSYNC_HOST=0.0.0.0 for network exposure.
    host = os.getenv("FARMSYNC_HOST", "127.0.0.1")
    port = int(os.getenv("FARMSYNC_PORT", "8000"))
    uvicorn.run("farmsync.server:app", host=host, port=port, reload=False)
