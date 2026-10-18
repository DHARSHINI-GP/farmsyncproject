"""Authenticated product workflows layered on the existing GIS application."""
import asyncio
import json
from pathlib import Path
import time
from contextlib import asynccontextmanager

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field, SecretStr
from farmsync.aws import TextModelId


class LoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: SecretStr


class UserInput(LoginInput):
    role: str = "user"


class JobInput(BaseModel):
    model_id: TextModelId | None = None
    query: str = Field(min_length=1, max_length=8000)
    survey_no: str | None = None
    parcel_id: str | None = None
    image_filename: str | None = None
    document_path: str | None = None
    force_escalate: bool = False
    simulate_conflict: bool = False


class ReviewInput(BaseModel):
    resolution: str = Field(min_length=5, max_length=4000)


class BatchInput(BaseModel):
    document_path: str = Field(max_length=1024)
    village: str | None = Field(default=None, max_length=128)


def capability_summary(orchestrator):
    from farmsync.vision.train_crop_model import CROP_CLASSES, STAGE_CLASSES
    corpus = orchestrator.knowledge.corpus
    pairs = {(str(d.get('crop')), str(d.get('growth_stage'))) for d in corpus}
    return {'ownership_verification': 'UNVERIFIED_DEMONSTRATION_ONLY',
            'crop_health_diagnosis': 'UNSUPPORTED_NO_VALIDATED_HEALTH_LABELS',
            'crop_classes': CROP_CLASSES, 'growth_stages': STAGE_CLASSES,
            'advisory_entries': len(corpus), 'advisory_pairs': sorted(pairs),
            'uncovered_pairs': [[c,s] for c in CROP_CLASSES for s in STAGE_CLASSES if (c,s) not in pairs],
            'source_scope': 'Supplied datasets; missing evidence is not invented',
            'trust_score_kind': 'HEURISTIC_EVIDENCE_SCORE_NOT_A_PROBABILITY',
            'planner': 'Bounded domain DAG composition with validated fallback; no arbitrary tool execution'}


def install(app, runtime):
    router = APIRouter()

    @asynccontextmanager
    async def lifespan(_app):
        runtime.startup()
        try:
            yield
        finally:
            await asyncio.to_thread(runtime.shutdown)
    app.router.lifespan_context = lifespan

    @router.get("/health/live")
    def live():
        return {"status": "alive"}

    @router.get("/health/ready")
    def ready(response: Response):
        try:
            with runtime.store.connect() as db:
                db.execute("SELECT 1").fetchone()
            okay = len(runtime.orchestrator.spatial.gdf_parcels_wgs84) > 0
            okay = okay and (not runtime.production or runtime.store.admin_count() > 0)
        except Exception:
            okay = False
        response.status_code = 200 if okay else 503
        return {"ready": okay, "vision_local_ready": runtime.orchestrator.vision.mobilenet is not None,
                "cloud_note": "Cloud availability is checked separately; a constructed client is not a live check"}

    @router.get("/api/auth/status")
    def auth_status(request: Request):
        user = runtime.resolve_session(request)
        return {"authenticated": bool(user), "user": user, "login_required": runtime.production or runtime.store.user_count() > 0,
                "production": runtime.production}

    @router.get("/api/capabilities")
    def capabilities():
        return capability_summary(runtime.orchestrator)

    @router.get("/api/admin/metrics")
    def metrics(request: Request):
        runtime.admin(request)
        with runtime.store.connect() as db:
            states = {r[0]: r[1] for r in db.execute("SELECT status,COUNT(*) FROM runs GROUP BY status")}
            usage = {r[0]: r[1] for r in db.execute("SELECT category,COUNT(*) FROM usage WHERE created>? GROUP BY category", (time.time() - 86400,))}
            records = db.execute("SELECT result FROM runs WHERE status='COMPLETED' ORDER BY created DESC LIMIT 1000").fetchall()
        tokens = 0
        for record in records:
            result = json.loads(record[0])
            tokens += (result.get("tokens") or {}).get("total_tokens", 0)
            tokens += sum((result.get("routing_telemetry", {}).get("planning_usage") or {}).get(k, 0) for k in ("inputTokens", "outputTokens"))
        return {"runs_by_status": states, "admitted_operations_last_24h": usage,
                "reported_model_tokens_last_1000_runs": tokens,
                "cost_notice": "Token counts exclude unreported provider usage and are not an actual AWS bill"}

    @router.post("/api/auth/login")
    def login(payload: LoginInput, request: Request, response: Response):
        client = request.client.host if request.client else "unknown"
        if not runtime.store.admit("login:" + client, "login", 8, 300):
            raise HTTPException(429, "Too many sign-in attempts; retry later")
        result = runtime.store.login(payload.username, payload.password.get_secret_value())
        if not result:
            raise HTTPException(401, "Invalid username or password")
        token, user = result
        response.set_cookie("farmsync_session", token, httponly=True, secure=runtime.production, samesite="strict", max_age=8 * 3600)
        runtime.store.event(user["id"], "SIGNED_IN", {})
        return {"user": user}

    @router.post("/api/auth/logout")
    def logout(request: Request, response: Response):
        token = request.cookies.get("farmsync_session")
        if request.headers.get('authorization','').lower().startswith('bearer '):
            token = request.headers['authorization'][7:]
        if token:
            runtime.store.logout(token)
        response.delete_cookie("farmsync_session")
        return {"signed_out": True}

    @router.post("/api/users", status_code=201)
    def create_user(payload: UserInput, request: Request):
        runtime.admin(request)
        try:
            return runtime.store.create_user(payload.username, payload.password.get_secret_value(), payload.role)
        except Exception as exc:
            raise HTTPException(400, "Cannot create this user; check username, password length, uniqueness and role") from exc

    @router.post("/api/images/upload")
    async def upload_image(request: Request, file: UploadFile = File(...), latitude: float | None = Form(default=None), longitude: float | None = Form(default=None), survey_no: str | None = Form(default=None)):
        if (latitude is None) != (longitude is None) or (latitude is not None and not (-90 <= latitude <= 90 and -180 <= longitude <= 180)):
            raise HTTPException(422, "Provide a valid latitude/longitude pair or leave both blank")
        return await runtime.upload(request, file, "image", {"latitude": latitude, "longitude": longitude, "survey_no": survey_no})

    @router.get("/api/assets")
    def list_assets(request: Request):
        user = runtime.user(request)
        return {"assets": runtime.store.assets(user["id"])}

    @router.get("/api/assets/{asset_id}/file")
    def asset_file(asset_id: str, request: Request):
        user = runtime.user(request)
        asset = runtime.store.asset(asset_id, user["id"], admin=user["role"] == "admin")
        if not asset and user["role"] == "reviewer":
            asset = runtime.store.reviewer_asset(asset_id, user["id"])
        if not asset:
            raise HTTPException(404, "Evidence not found")
        return FileResponse(asset["path"], media_type="application/pdf" if asset["kind"] == "pdf" else "image/jpeg", filename=asset["original_name"])

    @router.post("/api/assets/{asset_id}/archive")
    def archive_asset(asset_id: str, request: Request):
        user = runtime.user(request)
        if not runtime.store.asset(asset_id, user["id"]):
            raise HTTPException(404, "Evidence not found")
        with runtime.store.connect() as db:
            db.execute("UPDATE assets SET deleted=1 WHERE id=? AND owner=?", (asset_id, user["id"]))
        runtime.store.event(user["id"], "ASSET_ARCHIVED", {"asset_id": asset_id})
        return {"archived": True, "recoverable": True}

    @router.post("/api/assets/{asset_id}/restore")
    def restore_asset(asset_id: str, request: Request):
        user = runtime.user(request)
        with runtime.store.connect() as db:
            count = db.execute("UPDATE assets SET deleted=0 WHERE id=? AND owner=?", (asset_id, user["id"])).rowcount
        if not count:
            raise HTTPException(404, "Evidence not found")
        runtime.store.event(user["id"], "ASSET_RESTORED", {"asset_id": asset_id})
        return {"restored": True}

    @router.post("/api/jobs", status_code=202)
    def submit_job(payload: JobInput, request: Request):
        run_id = runtime.submit(runtime.user(request), payload.model_dump())
        return {"run_id": run_id, "events_url": f"/api/jobs/{run_id}/events"}

    @router.get("/api/runs")
    def history(request: Request):
        return {"runs": runtime.store.runs(runtime.user(request)["id"])}

    @router.get("/api/runs/{run_id}")
    @router.get("/api/jobs/{run_id}")
    def run_detail(run_id: str, request: Request):
        user = runtime.user(request)
        allowed = user["role"] == "admin" or (user["role"] == "reviewer" and runtime.store.can_review_run(run_id, user["id"]))
        result = runtime.store.run(run_id, user["id"], reviewer=allowed)
        if not result:
            raise HTTPException(404, "Run not found")
        return result

    @router.post("/api/jobs/{run_id}/cancel")
    def cancel_job(run_id: str, request: Request):
        if not runtime.store.cancel(run_id, runtime.user(request)["id"]):
            raise HTTPException(409, "No active owned job to cancel")
        return {"cancellation_requested": True, "notice": "Cancellation is checked between bounded tool calls; an active inference is allowed to return safely"}

    @router.get("/api/runs/{run_id}/export")
    def export_run(run_id: str, request: Request):
        result = run_detail(run_id, request)
        return Response(json.dumps(result, ensure_ascii=False, indent=2), media_type="application/json", headers={"Content-Disposition": f'attachment; filename="farmsync-{run_id}.json"'})

    @router.get("/api/jobs/{run_id}/events")
    async def job_events(run_id: str, request: Request):
        user = runtime.user(request)
        if not runtime.store.run(run_id, user["id"]):
            raise HTTPException(404, "Run not found")
        try:
            cursor = int(request.headers.get("last-event-id", "0"))
        except ValueError as exc:
            raise HTTPException(400, "Invalid event cursor") from exc
        async def stream():
            nonlocal cursor
            started = time.monotonic()
            while time.monotonic() - started < 120:
                if await request.is_disconnected():
                    return
                events = runtime.store.events(run_id, user["id"], cursor)
                for event in events:
                    cursor = event["id"]
                    yield f"id: {cursor}\ndata: {json.dumps(event)}\n\n"
                state = runtime.store.run(run_id, user["id"])
                if state["status"] in {"COMPLETED", "FAILED", "CANCELLED", "INTERRUPTED"} and not runtime.store.events(run_id, user["id"], cursor):
                    yield f"event: done\ndata: {json.dumps({'status': state['status']})}\n\n"
                    return
                yield ": heartbeat\n\n"
                await asyncio.sleep(1)
        return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @router.get("/api/reviews")
    def list_reviews(request: Request):
        user = runtime.user(request)
        return {"reviews": runtime.store.reviews(user["id"], reviewer=user["role"] in {"admin", "reviewer"})}

    @router.post("/api/reviews/{review_id}/resolve")
    def resolve_review(review_id: str, payload: ReviewInput, request: Request):
        user = runtime.user(request)
        if user["role"] not in {"admin", "reviewer"}:
            raise HTTPException(403, "Reviewer role required")
        if not runtime.store.resolve_review(review_id, user["id"], payload.resolution):
            raise HTTPException(404, "Open review not found")
        return {"resolved": True, "notice": "Human review records a decision; it does not manufacture official ownership or replace the source evidence"}

    @router.post("/api/documents/batch")
    def batch_document(payload: BatchInput, request: Request):
        user = runtime.user(request)
        if not runtime.store.admit(user["id"], "batch", 2):
            raise HTTPException(429, "Batch rate limit reached")
        from farmsync.documents.batch import compare_document
        if not runtime.lock.acquire(timeout=30):
            raise HTTPException(503, 'Processing capacity timeout')
        try:
            return compare_document(runtime, user, payload.model_dump())
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        finally:
            runtime.lock.release()

    app.include_router(router)
