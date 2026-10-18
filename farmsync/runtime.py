"""Bounded execution, scoped uploads and durable run/review management."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import io
import json
import logging
import os
from pathlib import Path
import threading
import time
import uuid

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError

from farmsync.storage import Store


class Runtime:
    def __init__(self, orchestrator, ai, store=None, asset_dir=None):
        self.orchestrator, self.ai = orchestrator, ai
        self.store = store or Store()
        self.lock = threading.Lock()
        self.slots = threading.BoundedSemaphore(4)
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="farmsync")
        self.asset_dir = Path(asset_dir) if asset_dir else self.store.path.parent / "assets"
        self.asset_dir.mkdir(parents=True, exist_ok=True)
        self.orchestrator.docs.private_asset_root = str(self.asset_dir.resolve())

    @property
    def production(self):
        return os.getenv("FARMSYNC_ENV", "development") == "production"

    def startup(self):
        if self.pool is None:
            self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="farmsync")
        if self.production:
            if not self.store.admin_count():
                raise RuntimeError("Production requires an active administrator; use scripts/manage.py create-user --role admin")
            if os.getenv("FARMSYNC_ALLOW_RUNTIME_CREDENTIALS", "false").lower() == "true":
                raise RuntimeError("Browser AWS credential editing is forbidden in production")
            origins = os.getenv("FARMSYNC_ALLOWED_ORIGINS", "").split(",")
            if not origins or any(not o.strip().startswith("https://") for o in origins):
                raise RuntimeError("Production requires explicit HTTPS origins")
        self.store.recover_interrupted()

    def shutdown(self):
        self.pool.shutdown(wait=True, cancel_futures=True)
        self.pool = None

    def user(self, request):
        principal = getattr(request.state, "principal", None)
        if not principal:
            raise HTTPException(401, "Authentication required")
        return principal

    def resolve_session(self, request):
        token = request.cookies.get("farmsync_session")
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:]
        principal = self.store.principal(token)
        if principal:
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                origin = request.headers.get("origin")
                allowed = {o.strip() for o in os.getenv("FARMSYNC_ALLOWED_ORIGINS", "http://127.0.0.1:8017,http://localhost:8000,http://127.0.0.1:8000").split(",")}
                if origin and origin not in allowed:
                    raise HTTPException(403, "Unapproved request origin")
            request.state.principal = principal
            return principal
        return None

    def admin(self, request):
        principal = self.user(request)
        if principal["role"] != "admin":
            raise HTTPException(403, "Administrator role required")
        return principal

    def authorize_payload(self, payload, user):
        payload = dict(payload)
        if payload.get("query"):
            from farmsync.router.compiler import TaskGraphCompiler
            try:
                TaskGraphCompiler.extract_buffer_distance(payload["query"])
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
        image_record = None
        for field, kind in (("document_path", "pdf"), ("image_filename", "image")):
            value = payload.get(field)
            if not value:
                continue
            if value.startswith("asset:"):
                asset = self.store.asset(value[6:], user["id"])
                if not asset or asset["kind"] != kind:
                    raise HTTPException(404, "Evidence not found")
                if sha256(Path(asset["path"]).read_bytes()).hexdigest() != asset["checksum"]:
                    raise HTTPException(409, "Evidence checksum changed; upload a new version")
                if kind == "pdf":
                    payload[field] = asset["path"]
                else:
                    image_record = {"filename": value, "filepath": asset["path"], **asset["metadata"]}
                    # Propagate survey_no from the request payload so the orchestrator
                    # can verify the image is associated with the correct cadastral parcel.
                    if payload.get("survey_no"):
                        image_record["survey_no"] = str(payload["survey_no"]).strip()
            elif field == "document_path":
                normalized = value.replace("\\", "/").casefold()
                candidate = Path(value).resolve()
                if "uploads" in normalized.split("/") or candidate.is_relative_to(self.asset_dir.resolve()):
                    raise HTTPException(403, "Private uploads require their owned asset ID")
        if self.production and (payload.get("simulate_conflict") or payload.get("simulate_ood")):
            raise HTTPException(400, "Simulation flags are disabled in production")
        return payload, image_record

    def analyze(self, user, payload, *, ai=True, run_id=None, event_callback=None):
        source_request = dict(payload)
        payload, record = self.authorize_payload(payload, user)
        if run_id is None:
            if not self.store.admit(user["id"], "analysis", int(os.getenv("FARMSYNC_ANALYSES_PER_MINUTE", "10"))):
                raise HTTPException(429, "Analysis rate limit reached")
            if not self.store.admit(user["id"], "analysis_day", int(os.getenv("FARMSYNC_ANALYSES_PER_DAY", "100")), 86400):
                raise HTTPException(429, "Daily analysis quota reached")
            run_id = self.store.create_run(user["id"], source_request)
        deadline = time.monotonic() + int(os.getenv("FARMSYNC_REQUEST_DEADLINE_SECONDS", "180"))

        def check_cancel():
            state = self.store.run(run_id, user["id"])
            if state["cancel_requested"]:
                raise RuntimeError("REQUEST_CANCELLED")
            if time.monotonic() > deadline:
                raise RuntimeError("REQUEST_DEADLINE_EXCEEDED")

        def progress(event):
            check_cancel()
            self.store.event(user["id"], "TASK_PROGRESS", event, run_id)
            if event_callback:
                event_callback(event)

        acquired = self.lock.acquire(timeout=max(0, deadline - time.monotonic()))
        if not acquired:
            self.store.update_run(run_id, "FAILED", error="Processing capacity timeout")
            raise HTTPException(503, "Processing capacity timeout")
        try:
            check_cancel()
            self.store.update_run(run_id, "RUNNING")
            self.store.event(user["id"], "RUNNING", {}, run_id)
            if record:
                self.orchestrator.vision.image_registry[record["filename"]] = record
            if ai:
                kwargs = {k: payload.get(k) for k in ("query", "survey_no", "document_path", "force_escalate", "simulate_conflict", "parcel_id", "image_filename", "model_id")}
                result = self.ai.process_query(**kwargs, event_callback=progress, cancel_check=check_cancel)
            else:
                kwargs = {k: payload.get(k) for k in ("query", "survey_no", "document_path", "simulate_conflict", "parcel_id", "image_filename")}
                kwargs.update(force_escalate_vision=payload.get("force_escalate", False), simulate_unsupported_crop=payload.get("simulate_ood", False))
                result = self.orchestrator.execute_request(**kwargs, event_callback=progress, cancel_check=check_cancel)
            check_cancel()
            result["run_id"] = run_id
            result["evidence_assets"] = []
            for field in ("document_path", "image_filename"):
                reference = source_request.get(field) or ""
                if reference.startswith("asset:"):
                    asset = self.store.asset(reference[6:], user["id"])
                    result["evidence_assets"].append({"id": asset["id"], "filename": asset["original_name"], "sha256": asset["checksum"], "kind": asset["kind"]})
            result["evidence_policy"] = "Source claims only; ownership and health are unverified without authoritative evidence"
            result["cost_notice"] = "Routing costs are estimates, not actual AWS billing. Token usage and actual Location calls are separate signals."
            self.store.update_run(run_id, "COMPLETED", result=result)
            self.store.event(user["id"], "COMPLETED", {"tokens": result.get("tokens"), "estimated_cost_usd": result.get("routing_telemetry", {}).get("total_estimated_cost_usd")}, run_id)
            vobj = result.get("verified_result_object", {})
            if vobj.get("trust_metrics", {}).get("verification_status") != "VERIFIED_ACCEPT":
                self.store.create_review(run_id, user["id"])
            return result
        except Exception as exc:
            logging.getLogger(__name__).exception("Analysis failed for run %s", run_id)
            code = str(exc) if str(exc) in {"REQUEST_CANCELLED", "REQUEST_DEADLINE_EXCEEDED"} else type(exc).__name__
            status = "CANCELLED" if code == "REQUEST_CANCELLED" else "FAILED"
            self.store.update_run(run_id, status, error=code)
            self.store.event(user["id"], status, {"error_code": code}, run_id)
            if isinstance(exc, HTTPException):
                raise
            raise HTTPException(503 if "DEADLINE" in code else 500, {"error": code, "run_id": run_id}) from exc
        finally:
            if record:
                self.orchestrator.vision.image_registry.pop(record["filename"], None)
            self.lock.release()

    def submit(self, user, payload):
        self.authorize_payload(payload, user)
        if not self.slots.acquire(blocking=False):
            raise HTTPException(429, "Job queue is full")
        if not self.store.admit(user["id"], "analysis", int(os.getenv("FARMSYNC_ANALYSES_PER_MINUTE", "10"))) or not self.store.admit(user["id"], "analysis_day", int(os.getenv("FARMSYNC_ANALYSES_PER_DAY", "100")), 86400):
            self.slots.release()
            raise HTTPException(429, "Analysis quota reached")
        run_id = self.store.create_run(user["id"], payload)
        def work():
            try:
                self.analyze(user, payload, run_id=run_id)
            except HTTPException:
                pass
            finally:
                self.slots.release()
        self.pool.submit(work)
        return run_id

    async def receive(self, file, limit):
        chunks, total = [], 0
        while chunk := await file.read(65536):
            total += len(chunk)
            if total > limit:
                raise HTTPException(413, "Upload exceeds the configured size limit")
            chunks.append(chunk)
        if not total:
            raise HTTPException(400, "Uploaded file is empty")
        return b"".join(chunks)

    async def upload(self, request, file, kind, metadata=None, limit=None):
        user = self.user(request)
        if not self.store.admit(user["id"], "upload", 20):
            raise HTTPException(429, "Upload rate limit reached")
        raw = await self.receive(file, limit or int(os.getenv("FARMSYNC_MAX_UPLOAD_SIZE", str(15 * 1024 * 1024))))
        name = Path((file.filename or "upload").replace("\\", "/")).name[:150]
        metadata = dict(metadata or {})
        if kind == "pdf":
            if not raw.startswith(b"%PDF"):
                raise HTTPException(400, "Invalid PDF file format: missing %PDF header")
            try:
                import pypdf
                pdf = pypdf.PdfReader(io.BytesIO(raw), strict=True)
                if pdf.is_encrypted or not 0 < len(pdf.pages) <= int(os.getenv("FARMSYNC_MAX_PDF_PAGES", "100")):
                    raise ValueError("Encrypted, empty or excessive-page PDF")
                metadata["page_count"] = len(pdf.pages)
            except Exception as exc:
                raise HTTPException(400, "PDF is invalid, encrypted or exceeds the page limit") from exc
            extension = ".pdf"
        else:
            try:
                with Image.open(io.BytesIO(raw)) as source:
                    if source.format not in {"JPEG", "PNG", "WEBP"} or source.width * source.height > 20_000_000:
                        raise ValueError("Unsupported image or pixel limit")
                    source.verify()
                with Image.open(io.BytesIO(raw)) as source:
                    image = ImageOps.exif_transpose(source).convert("RGB")
                    image.thumbnail((3000, 3000))
                    out = io.BytesIO()
                    image.save(out, "JPEG", quality=92)
                    raw = out.getvalue()
                    metadata.update(width=image.width, height=image.height, location_source="user supplied; image authenticity not independently verified")
            except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError) as exc:
                raise HTTPException(400, "Invalid image; upload a JPEG, PNG or WebP within the pixel limit") from exc
            extension = ".jpg"
        path = self.asset_dir / (uuid.uuid4().hex + extension)
        checksum = sha256(raw).hexdigest()
        try:
            with path.open("xb") as handle:
                handle.write(raw)
            asset_id = self.store.add_asset(user["id"], kind, name, path, checksum, metadata)
            if getattr(self, 'ephemeral_uploads', False):
                path.unlink(missing_ok=True)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        self.store.event(user["id"], "ASSET_CREATED", {"asset_id": asset_id, "kind": kind, "checksum": checksum})
        return {"status": "UPLOAD_SUCCESS", "asset_id": asset_id, "reference": "asset:" + asset_id, "filename": name, "saved_path": "asset:" + asset_id, "size_bytes": len(raw), "sha256": checksum, "metadata": metadata}
