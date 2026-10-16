import sys
import os
import io
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestRequirementsCompleteness:
    """
    Validates that requirements.txt specifies all essential production packages
    imported and required by the application.
    """

    def test_requirements_file_has_all_critical_packages(self):
        req_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "requirements.txt")
        assert os.path.exists(req_path), "requirements.txt must exist"

        with open(req_path, "r", encoding="utf-8") as f:
            req_content = f.read().lower()

        required_packages = [
            "torch",
            "torchvision",
            "pdfplumber",
            "jsonschema",
            "python-multipart",
            "faiss-cpu",
            "sentence-transformers",
            "geopandas",
            "shapely",
            "fastapi",
            "uvicorn",
            "streamlit",
            "numpy",
            "pandas",
            "boto3",
            "pytest"
        ]

        for pkg in required_packages:
            assert pkg in req_content, f"Critical package '{pkg}' missing from requirements.txt"


class TestCleanEnvironmentRobustness:
    """
    Validates that the server and orchestrator do not crash on startup
    in a clean environment where heavy packages like PyTorch, pdfplumber,
    or jsonschema might not be present or are running in degraded mode.
    """

    def test_vision_pipeline_graceful_when_torch_unavailable(self):
        """Simulates clean environment where torch/torchvision are not installed."""
        from farmsync.vision import classifier

        orig_available = classifier.TORCH_AVAILABLE
        orig_model = classifier.models
        try:
            # Force simulated clean environment without PyTorch
            classifier.TORCH_AVAILABLE = False
            classifier.models = None

            pipeline = classifier.CropVisionPipeline()
            assert pipeline.model is None
            assert pipeline.transform is None

            # Test missing photo still behaves safely
            res_none = pipeline.predict_crop(None)
            assert res_none["has_image"] is False

            # Test with image in clean environment returns degraded status, NOT crash
            dummy_img = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data", "FAI_Product_Challange", "TASK_4", "Images", "images", "Field.jpg"
            )
            if os.path.exists(dummy_img):
                res = pipeline.predict_crop(dummy_img)
                assert res["has_image"] is True
                assert res["status"] == "PYTORCH_NOT_INSTALLED"
                assert res["predicted_crop"] is None
                assert res["final_confidence"] == 0.0
        finally:
            classifier.TORCH_AVAILABLE = orig_available
            classifier.models = orig_model

    def test_trust_engine_graceful_when_jsonschema_unavailable(self):
        """Simulates clean environment where jsonschema is not installed."""
        from farmsync.trust import trust_score

        orig_available = trust_score.JSONSCHEMA_AVAILABLE
        orig_mod = trust_score.jsonschema
        try:
            trust_score.JSONSCHEMA_AVAILABLE = False
            trust_score.jsonschema = None

            engine = trust_score.TrustEngine()

            # Valid payload should still pass structural check
            valid_payload = {
                "survey_number": "384",
                "village": "Keelathattaparai",
                "extracted_attributes": {
                    "registered_owner": "Ramesh Kumar",
                    "gis_area_acres": 10.349,
                    "predicted_crop": "Coconut",
                    "growth_stage": "full_growth"
                },
                "deterministic_spatial_checks": {}
            }
            score_valid = engine.validate_output_schema(valid_payload)
            assert score_valid == 1.00

            # Incomplete payload should fail structural check
            invalid_payload = {
                "survey_number": "384"
            }
            score_invalid = engine.validate_output_schema(invalid_payload)
            assert score_invalid == 0.00
        finally:
            trust_score.JSONSCHEMA_AVAILABLE = orig_available
            trust_score.jsonschema = orig_mod

    def test_document_engine_initializes_when_pdfplumber_unavailable(self):
        """Simulates clean environment where pdfplumber is not installed."""
        from farmsync.documents import extractor

        orig_available = extractor.PDFPLUMBER_AVAILABLE
        orig_plumber = extractor.pdfplumber
        try:
            extractor.PDFPLUMBER_AVAILABLE = False
            extractor.pdfplumber = None

            doc_engine = extractor.DocumentRegistryEngine()
            assert doc_engine is not None
            assert len(doc_engine.cadastral_registry) > 0
        finally:
            extractor.PDFPLUMBER_AVAILABLE = orig_available
            extractor.pdfplumber = orig_plumber


class TestDocumentUploadEndpointMultipart:
    """
    Validates FastAPI document upload endpoint using python-multipart.
    """

    def test_upload_route_accepts_pdf(self):
        from fastapi.testclient import TestClient
        from farmsync.server import app

        client = TestClient(app)
        dummy_pdf_content = b"%PDF-1.4 test content for multipart upload verification"
        files = {
            "file": ("test_upload.pdf", io.BytesIO(dummy_pdf_content), "application/pdf")
        }

        response = client.post("/api/documents/upload", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "UPLOAD_SUCCESS"
        assert data["filename"] == "test_upload.pdf"
        assert data["size_bytes"] == len(dummy_pdf_content)

    def test_upload_route_rejects_non_pdf(self):
        from fastapi.testclient import TestClient
        from farmsync.server import app

        client = TestClient(app)
        files = {
            "file": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")
        }

        response = client.post("/api/documents/upload", files=files)
        assert response.status_code == 400
        assert "Only PDF files are supported" in response.json()["detail"]
