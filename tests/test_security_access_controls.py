import io
import os
import pytest
from fastapi.testclient import TestClient

from farmsync.server import app, sanitize_upload_filename, MAX_UPLOAD_SIZE_BYTES, ALLOWED_ORIGINS


class TestUploadFilenameSanitization:
    """
    Verifies that client-supplied filenames cannot perform directory traversal
    or inject malicious filesystem characters.
    """

    def test_sanitize_normal_pdf_filename(self):
        clean = sanitize_upload_filename("revenue_patta_384.pdf")
        assert clean == "revenue_patta_384.pdf"

    def test_sanitize_path_traversal_relative_unix(self):
        clean = sanitize_upload_filename("../../../../etc/passwd.pdf")
        assert clean == "passwd.pdf"
        assert "/" not in clean
        assert ".." not in clean

    def test_sanitize_path_traversal_windows(self):
        clean = sanitize_upload_filename("..\\..\\Windows\\System32\\cmd.pdf")
        assert clean == "cmd.pdf"
        assert "\\" not in clean
        assert ".." not in clean

    def test_sanitize_replaces_illegal_characters(self):
        clean = sanitize_upload_filename("doc;rm -rf;><|.pdf")
        assert clean.endswith(".pdf")
        for bad_char in [";", ">", "<", "|"]:
            assert bad_char not in clean

    def test_sanitize_rejects_non_pdf_extension(self):
        with pytest.raises(Exception) as exc:
            sanitize_upload_filename("exploit.sh")
        assert "Only PDF files are supported" in str(exc.value)

    def test_sanitize_rejects_null_byte(self):
        with pytest.raises(Exception) as exc:
            sanitize_upload_filename("exploit\0.pdf")
        assert "Invalid character" in str(exc.value) or "invalid" in str(exc.value).lower()


class TestUploadPayloadValidation:
    """
    Verifies upload size limits and PDF magic byte signature validation.
    """

    def test_upload_rejects_non_pdf_signature(self):
        client = TestClient(app)
        fake_pdf = io.BytesIO(b"MZ This is an executable binary disguised as a PDF file")
        files = {"file": ("malicious.pdf", fake_pdf, "application/pdf")}

        response = client.post("/api/documents/upload", files=files)
        assert response.status_code == 400
        assert "missing %PDF header" in response.json()["detail"]

    def test_upload_rejects_empty_file(self):
        client = TestClient(app)
        empty_pdf = io.BytesIO(b"")
        files = {"file": ("empty.pdf", empty_pdf, "application/pdf")}

        response = client.post("/api/documents/upload", files=files)
        assert response.status_code == 400

    def test_upload_accepts_valid_pdf_with_magic_bytes(self):
        client = TestClient(app)
        valid_pdf = io.BytesIO(b"%PDF-1.5 authentic land document content for survey audit")
        files = {"file": ("valid_doc.pdf", valid_pdf, "application/pdf")}

        response = client.post("/api/documents/upload", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "UPLOAD_SUCCESS"
        assert data["filename"] == "valid_doc.pdf"

    def test_upload_rejects_oversized_payload(self, monkeypatch):
        # Set max upload size to 100 KB for test
        monkeypatch.setattr("farmsync.server.MAX_UPLOAD_SIZE_BYTES", 100 * 1024)

        client = TestClient(app)
        large_content = b"%PDF-1.4 " + (b"A" * (120 * 1024)) # 120 KB > 100 KB
        files = {"file": ("oversized.pdf", io.BytesIO(large_content), "application/pdf")}

        response = client.post("/api/documents/upload", files=files)
        assert response.status_code == 413
        assert "exceeds maximum allowed size" in response.json()["detail"]


class TestAccessControlsAndAuthentication:
    """
    Verifies access controls on sensitive endpoints (/api/settings/aws and /api/documents/upload).
    """

    def test_local_loopback_client_permitted_without_key_in_dev(self, monkeypatch):
        monkeypatch.setenv("FARMSYNC_ALLOW_RUNTIME_CREDENTIALS", "true")
        # When FARMSYNC_API_KEY is not set, local loopback (testclient) is permitted
        monkeypatch.delenv("FARMSYNC_API_KEY", raising=False)

        client = TestClient(app)
        res = client.post(
            "/api/settings/aws",
            json={
                "access_key_id": "test_id",
                "secret_access_key": "test_secret",
                "region": "ap-south-1"
            }
        )
        assert res.status_code == 200

    def test_external_network_client_rejected_when_unauthenticated(self, monkeypatch):
        # Simulate request from external network host (e.g. 192.168.1.105)
        monkeypatch.delenv("FARMSYNC_API_KEY", raising=False)

        client = TestClient(app, client=("192.168.1.105", 54321))
        res = client.post(
            "/api/settings/aws",
            json={
                "access_key_id": "attacker_key",
                "secret_access_key": "attacker_secret"
            }
        )
        assert res.status_code == 401
        assert "Unauthorized" in res.json()["detail"]

    def test_external_network_client_upload_rejected_when_unauthenticated(self, monkeypatch):
        monkeypatch.delenv("FARMSYNC_API_KEY", raising=False)

        client = TestClient(app, client=("192.168.1.105", 54321))
        files = {"file": ("doc.pdf", io.BytesIO(b"%PDF-test"), "application/pdf")}
        res = client.post("/api/documents/upload", files=files)
        assert res.status_code == 401

    def test_configured_api_key_enforced_strictly(self, monkeypatch):
        monkeypatch.setenv("FARMSYNC_ALLOW_RUNTIME_CREDENTIALS", "true")
        secret_key = "farmsync-secure-enterprise-key-2026"
        monkeypatch.setenv("FARMSYNC_API_KEY", secret_key)

        client = TestClient(app, client=("192.168.1.105", 54321))

        # 1. No key provided -> 401
        res = client.post(
            "/api/settings/aws",
            json={"access_key_id": "key", "secret_access_key": "sec"}
        )
        assert res.status_code == 401

        # 2. Wrong key provided -> 401
        res = client.post(
            "/api/settings/aws",
            headers={"X-API-Key": "wrong-key-value"},
            json={"access_key_id": "key", "secret_access_key": "sec"}
        )
        assert res.status_code == 401

        # 3. Valid key in X-API-Key header -> 200
        res = client.post(
            "/api/settings/aws",
            headers={"X-API-Key": secret_key},
            json={"access_key_id": "key", "secret_access_key": "sec"}
        )
        assert res.status_code == 200

        # 4. Valid key in Authorization: Bearer header -> 200
        res = client.post(
            "/api/settings/aws",
            headers={"Authorization": f"Bearer {secret_key}"},
            json={"access_key_id": "key", "secret_access_key": "sec"}
        )
        assert res.status_code == 200

        # 5. Valid key in JSON body -> 200
        res = client.post(
            "/api/settings/aws",
            json={"access_key_id": "key", "secret_access_key": "sec", "api_key": secret_key}
        )
        assert res.status_code == 200


class TestCORSAndNetworkBindingControls:
    """
    Verifies that CORS origins are restricted and wildcard CORS is not active.
    """

    def test_wildcard_cors_not_allowed_by_default(self):
        assert "*" not in ALLOWED_ORIGINS
        assert any("localhost" in orig or "127.0.0.1" in orig for orig in ALLOWED_ORIGINS)
