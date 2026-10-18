from io import BytesIO
from types import SimpleNamespace

from fastapi.testclient import TestClient
from PIL import Image
import pytest
from reportlab.pdfgen import canvas

from farmsync.server import app, runtime
from farmsync.storage import Store


@pytest.fixture
def platform(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime, "store", Store(tmp_path / "app.sqlite3"))
    monkeypatch.setattr(runtime, "asset_dir", tmp_path / "assets")
    runtime.asset_dir.mkdir()
    monkeypatch.setattr(runtime.orchestrator.docs, "private_asset_root", str(runtime.asset_dir))
    monkeypatch.delenv("FARMSYNC_API_KEY", raising=False)
    monkeypatch.setenv("FARMSYNC_ENV", "development")
    alice = runtime.store.create_user("alice", "alice-strong-password")
    bob = runtime.store.create_user("bob", "bob-strong-password")
    admin = runtime.store.create_user("admin", "admin-strong-password", "admin")
    with TestClient(app) as client:
        yield client, alice, bob, admin


def sign_in(client, username="alice"):
    response = client.post("/api/auth/login", json={"username": username, "password": username + "-strong-password"})
    assert response.status_code == 200


def pdf_bytes():
    output = BytesIO()
    c = canvas.Canvas(output)
    c.drawString(40, 750, "Survey 384; Owner: Actual Name; Area: 2 acres")
    c.save()
    return output.getvalue()


def test_accounts_disable_loopback_bypass_and_scope_assets(platform):
    client, alice, bob, _ = platform
    assert client.get("/api/assets").status_code == 401
    sign_in(client)
    first = client.post("/api/documents/upload", files={"file": ("same.pdf", pdf_bytes(), "application/pdf")})
    second = client.post("/api/documents/upload", files={"file": ("same.pdf", pdf_bytes(), "application/pdf")})
    assert first.status_code == second.status_code == 200
    assert first.json()["asset_id"] != second.json()["asset_id"]
    asset_id = first.json()["asset_id"]
    assert client.get(f"/api/assets/{asset_id}/file").status_code == 200
    client.post("/api/auth/logout")
    sign_in(client, "bob")
    assert client.get(f"/api/assets/{asset_id}/file").status_code == 404
    assert client.get("/api/assets").json()["assets"] == []
    assert client.post("/api/ai/query", json={"query": "Inspect Survey 384", "document_path": "asset:" + asset_id}).status_code == 404


def test_corrupt_files_and_cookie_origin_are_rejected(platform):
    client, *_ = platform
    sign_in(client)
    assert client.post("/api/documents/upload", files={"file": ("fake.pdf", b"%PDF-not-a-real-pdf", "application/pdf")}).status_code == 400
    assert client.post("/api/images/upload", files={"file": ("fake.jpg", b"not an image", "image/jpeg")}).status_code == 400
    assert client.post("/api/auth/logout", headers={"Origin": "https://attacker.invalid"}).status_code == 403


def test_real_image_upload_and_asset_archival(platform):
    client, *_ = platform
    sign_in(client)
    output = BytesIO()
    Image.new("RGB", (32, 32), "green").save(output, "PNG")
    response = client.post("/api/images/upload", files={"file": ("field.png", output.getvalue(), "image/png")}, data={"latitude": "8.7", "longitude": "78.0"})
    assert response.status_code == 200
    asset = response.json()
    assert asset["metadata"]["width"] == 32
    assert client.get("/api/image/" + asset["reference"]).status_code == 200
    assert client.post(f"/api/assets/{asset['asset_id']}/archive").status_code == 200
    assert client.get("/api/image/" + asset["reference"]).status_code == 404
    assert client.post(f"/api/assets/{asset['asset_id']}/restore").status_code == 200


@pytest.mark.parametrize("force_escalate", [False, True])
def test_uploaded_photo_preview_reference_survives_analysis(platform, monkeypatch, force_escalate):
    client, *_ = platform
    sign_in(client)
    output = BytesIO()
    Image.new("RGB", (32, 32), "green").save(output, "PNG")
    asset = client.post("/api/images/upload", files={"file": ("field.png", output.getvalue(), "image/png")}).json()

    def predict(path, **kwargs):
        # Inference returns the disk basename, not an authorized asset reference.
        from pathlib import Path
        return {"has_image": True, "image_filename": Path(path).name,
                "predicted_crop": "Coconut", "predicted_stage": "full_growth",
                "final_verified_crop": "Coconut", "final_verified_stage": "full_growth",
                "confidence": 0.99, "final_confidence": 0.99,
                "shannon_entropy": 0.01, "student_model": "test model",
                "escalated_to_teacher": False, "is_out_of_distribution": False}

    monkeypatch.setattr(runtime.orchestrator.vision, "predict_crop", predict)
    response = client.post("/api/orchestrate", json={
        "query": "Inspect Survey 384 crop and land evidence", "survey_no": "384",
        "image_filename": asset["reference"], "force_escalate": force_escalate})
    assert response.status_code == 200, response.text
    evidence = response.json()["verified_result_object"]["source_evidence"]
    photo = next(item for item in evidence if item["source_type"] == "FIELD_PHOTOGRAPH")
    assert photo["source_ref"] == asset["reference"]
    assert photo["parcel_location_verified"] is False
    preview = client.get("/api/image/" + photo["source_ref"])
    assert preview.status_code == 200
    assert preview.headers["content-type"] == "image/jpeg"
    client.post("/api/auth/logout")
    sign_in(client, "bob")
    assert client.get("/api/image/" + photo["source_ref"]).status_code == 404


def test_admin_actions_reviewer_permissions_and_production_gate(platform, monkeypatch):
    client, *_ = platform
    sign_in(client)
    assert client.post("/api/users", json={"username": "newuser", "password": "new-strong-password"}).status_code == 403
    assert client.post("/api/settings/aws/check").status_code == 403
    client.post("/api/auth/logout")
    sign_in(client, "admin")
    assert client.post("/api/users", json={"username": "newuser", "password": "new-strong-password"}).status_code == 201
    monkeypatch.setenv("FARMSYNC_ENV", "production")
    monkeypatch.setenv("FARMSYNC_ALLOWED_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="HTTPS"):
        runtime.startup()


def test_jobs_stream_progress_save_history_and_export(platform, monkeypatch):
    client, *_ = platform
    def process_query(**kwargs):
        assert kwargs["model_id"] == "mistral.ministral-3-8b-instruct"
        kwargs["event_callback"]({"task_id": "test", "status": "RUNNING"})
        return {"answer": "Only source facts", "verified_result_object": {"trust_metrics": {"verification_status": "VERIFIED_ABSTAIN"}}, "tokens": {"total_tokens": 7}}
    monkeypatch.setattr(runtime.ai, "process_query", process_query)
    sign_in(client)
    response = client.post("/api/jobs", json={"query": "Inspect Survey 384", "model_id": "mistral.ministral-3-8b-instruct"})
    assert response.status_code == 202
    run_id = response.json()["run_id"]
    with client.stream("GET", f"/api/jobs/{run_id}/events") as stream:
        text = "".join(stream.iter_text())
    assert "TASK_PROGRESS" in text and "event: done" in text
    assert client.get(f"/api/runs/{run_id}").json()["result"]["answer"] == "Only source facts"
    assert client.get(f"/api/runs/{run_id}/export").status_code == 200
    assert client.get("/api/reviews").json()["reviews"]
    client.post("/api/auth/logout")
    sign_in(client, "bob")
    assert client.get(f"/api/runs/{run_id}").status_code == 404


def test_ai_request_validates_and_passes_model_selection(platform, monkeypatch):
    client, *_ = platform
    sign_in(client)
    selected = "mistral.ministral-3-8b-instruct"
    def process_query(**kwargs):
        assert kwargs["model_id"] == selected
        return {"answer": "Test response", "verified_result_object": {"trust_metrics": {"verification_status": "VERIFIED_ABSTAIN"}}}
    monkeypatch.setattr(runtime.ai, "process_query", process_query)
    assert client.post("/api/ai/query", json={"query": "Inspect Survey 384", "model_id": selected}).status_code == 200
    for endpoint in ("/api/ai/query", "/api/jobs"):
        assert client.post(endpoint, json={"query": "Inspect Survey 384", "model_id": "unapproved-model"}).status_code == 422


def test_batch_compares_explicit_source_claims(platform):
    client, *_ = platform
    sign_in(client)
    uploaded = client.post("/api/documents/upload", files={"file": ("batch.pdf", pdf_bytes(), "application/pdf")}).json()
    result = client.post("/api/documents/batch", json={"document_path": uploaded["reference"], "village": "Keelathattaparai"})
    assert result.status_code == 200
    data = result.json()
    assert data["total_claims"] == 1
    assert data["claims"][0]["claim"]["extracted_owner"] == "Actual Name"
    assert data["ownership_verified"] is False
