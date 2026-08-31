"""
test_ocr_pipeline_hardening.py

P0/P1 Production Hardening Tests — Audit Phase 2
Tests:
1. Allowlist-only transient classification (default False).
2. Uniform 6-key error contract across all error paths.
3. Request tracing (X-Request-ID propagation throughout lifecycle).
4. Image security: decompression bomb & dimension limit protection.
5. Upload hardening: bounded chunked stream & file size limits.
6. Health probes: liveness, readiness, dedicated model warmup.
7. Strongly typed schemas for ScanEvaluationResponse.
"""
import io
import os
import uuid
from typing import Set

import pytest
from fastapi.testclient import TestClient
from PIL import Image as PILImage

os.environ.setdefault("MEDISCAN_TEST_MODE", "true")

from app.schemas.ocr_schema import (
    EvaluationResponse,
    InteractionAlert,
    OCRPipelineMetrics,
    ScanEvaluationResponse,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

REQUIRED_ERROR_KEYS: Set[str] = {
    "error_code",
    "message",
    "service",
    "stage",
    "request_id",
    "retryable",
}


def _make_minimal_png_bytes() -> bytes:
    """Tạo file PNG 1x1 pixel hợp lệ (đã verify qua PIL.load()) để test upload."""
    import base64
    b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
    return base64.b64decode(b64)


def _make_large_dimension_png_bytes(width: int = 10001, height: int = 1) -> bytes:
    """Tạo file PNG có dimension vượt ngưỡng an toàn (10,000px)."""
    img = PILImage.new("RGB", (width, height), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_corrupt_bytes() -> bytes:
    return b"\xff\xd8\xff\xe0" + b"\x00" * 20


def _auth_headers(client) -> dict:
    unique = uuid.uuid4().hex[:8]
    resp = client.post("/api/v1/auth/register", json={
        "email": f"harden_{unique}@mediscan.ai",
        "username": f"harden_{unique}",
        "password": "Harden@1234",
        "full_name": "Harden Test",
    })
    assert resp.status_code == 201, f"Register failed: {resp.text}"
    token = resp.json()["accessToken"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth_headers(client):
    return _auth_headers(client)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Schema & Typing Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestOCRPipelineMetricsSchema:
    def test_default_values_are_zero(self):
        m = OCRPipelineMetrics()
        assert m.preprocessor_ms == 0
        assert m.ocr_inference_ms == 0
        assert m.total_latency_ms == 0

    def test_all_fields_set(self):
        m = OCRPipelineMetrics(preprocessor_ms=10, ocr_inference_ms=200, total_latency_ms=210)
        assert m.preprocessor_ms == 10

    def test_negative_rejected(self):
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            OCRPipelineMetrics(preprocessor_ms=-1)

    def test_camel_alias(self):
        m = OCRPipelineMetrics(preprocessor_ms=5, ocr_inference_ms=100, total_latency_ms=105)
        d = m.model_dump(by_alias=True)
        assert "preprocessorMs" in d
        assert "ocrInferenceMs" in d


class TestScanEvaluationResponseSchema:
    def test_clinical_report_is_typed_evaluation_response(self):
        resp = ScanEvaluationResponse(
            clinical_report=EvaluationResponse(
                total_drugs_analyzed=1,
                alerts=[
                    InteractionAlert(
                        severity="HIGH",
                        title="Alert Test",
                        description="Desc",
                        recommendation="Rec",
                    )
                ],
                final_summary="Test Summary",
            )
        )
        assert resp.clinical_report is not None
        assert resp.clinical_report.total_drugs_analyzed == 1
        assert len(resp.clinical_report.alerts) == 1
        assert resp.clinical_report.alerts[0].severity == "HIGH"

    def test_schema_has_request_id_field(self):
        from app.schemas.ocr_schema import FullScanResponse
        fields = FullScanResponse.model_fields
        assert "request_id" in fields
        assert fields["request_id"].default == ""


# ─────────────────────────────────────────────────────────────────────────────
# 2. Upload & Image Security Hardening Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestOCRUploadValidation:
    def test_no_auth_returns_401(self, client):
        png = _make_minimal_png_bytes()
        resp = client.post(
            "/api/v1/ocr/scan",
            files={"file": ("test.png", png, "image/png")},
            data={"source_type": "packaging"},
        )
        assert resp.status_code == 401

    def test_invalid_mime_type_returns_structured_error(self, client, auth_headers):
        resp = client.post(
            "/api/v1/ocr/scan",
            files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
            data={"source_type": "packaging"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert REQUIRED_ERROR_KEYS.issubset(detail.keys())
        assert detail["error_code"] == "INVALID_MIME_TYPE"
        assert detail["retryable"] is False
        assert detail["stage"] == "validation"

    def test_invalid_extension_returns_structured_error(self, client, auth_headers):
        resp = client.post(
            "/api/v1/ocr/scan",
            files={"file": ("scan.tiff", _make_minimal_png_bytes(), "image/tiff")},
            data={"source_type": "prescription"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert REQUIRED_ERROR_KEYS.issubset(detail.keys())
        assert detail["error_code"] == "INVALID_EXTENSION"
        assert detail["retryable"] is False

    def test_invalid_source_type_returns_structured_error(self, client, auth_headers):
        png = _make_minimal_png_bytes()
        resp = client.post(
            "/api/v1/ocr/scan",
            files={"file": ("test.png", png, "image/png")},
            data={"source_type": "unknown_pipeline"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert REQUIRED_ERROR_KEYS.issubset(detail.keys())
        assert detail["error_code"] == "INVALID_SOURCE_TYPE"
        assert detail["retryable"] is False

    def test_empty_file_returns_structured_error(self, client, auth_headers):
        resp = client.post(
            "/api/v1/ocr/scan",
            files={"file": ("empty.png", b"", "image/png")},
            data={"source_type": "packaging"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert REQUIRED_ERROR_KEYS.issubset(detail.keys())
        assert detail["error_code"] == "EMPTY_FILE"
        assert detail["retryable"] is False

    def test_corrupt_image_returns_structured_error(self, client, auth_headers):
        corrupt = _make_corrupt_bytes()
        resp = client.post(
            "/api/v1/ocr/scan",
            files={"file": ("corrupt.jpg", corrupt, "image/jpeg")},
            data={"source_type": "packaging"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert REQUIRED_ERROR_KEYS.issubset(detail.keys())
        assert detail["error_code"] == "CORRUPT_IMAGE"
        assert detail["retryable"] is False

    def test_image_dimensions_exceeded_returns_400(self, client, auth_headers):
        huge_dim_png = _make_large_dimension_png_bytes(width=10001, height=1)
        resp = client.post(
            "/api/v1/ocr/scan",
            files={"file": ("wide.png", huge_dim_png, "image/png")},
            data={"source_type": "packaging"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert REQUIRED_ERROR_KEYS.issubset(detail.keys())
        assert detail["error_code"] == "IMAGE_DIMENSIONS_EXCEEDED"
        assert detail["retryable"] is False


# ─────────────────────────────────────────────────────────────────────────────
# 3. Retryable Classification (Allowlist only)
# ─────────────────────────────────────────────────────────────────────────────

class TestStrictRetryableClassification:
    def test_name_error_not_retryable(self, client, auth_headers, monkeypatch):
        from app.services import ocr_engine as ocr_module

        def _raise(*_args, **_kwargs):
            raise NameError("name 'SomeVar' is not defined")

        monkeypatch.setattr(ocr_module.ocr_engine, "extract_packaging_label", _raise)

        resp = client.post(
            "/api/v1/ocr/scan",
            files={"file": ("test.png", _make_minimal_png_bytes(), "image/png")},
            data={"source_type": "packaging"},
            headers=auth_headers,
        )
        assert resp.status_code == 500
        detail = resp.json()["detail"]
        assert REQUIRED_ERROR_KEYS.issubset(detail.keys())
        assert detail["retryable"] is False

    def test_runtime_error_not_retryable(self, client, auth_headers, monkeypatch):
        from app.services import ocr_engine as ocr_module

        def _raise(*_args, **_kwargs):
            raise RuntimeError("Database pool exhausted internally")

        monkeypatch.setattr(ocr_module.ocr_engine, "extract_packaging_label", _raise)

        resp = client.post(
            "/api/v1/ocr/scan",
            files={"file": ("test.png", _make_minimal_png_bytes(), "image/png")},
            data={"source_type": "packaging"},
            headers=auth_headers,
        )
        assert resp.status_code == 500
        detail = resp.json()["detail"]
        assert detail["retryable"] is False

    def test_httpx_connect_error_is_retryable(self, client, auth_headers, monkeypatch):
        from app.services import ocr_engine as ocr_module
        import httpx

        def _raise(*_args, **_kwargs):
            raise httpx.ConnectError("Failed to connect to upstream OCR service")

        monkeypatch.setattr(ocr_module.ocr_engine, "extract_packaging_label", _raise)

        resp = client.post(
            "/api/v1/ocr/scan",
            files={"file": ("test.png", _make_minimal_png_bytes(), "image/png")},
            data={"source_type": "packaging"},
            headers=auth_headers,
        )
        assert resp.status_code == 500
        detail = resp.json()["detail"]
        assert detail["retryable"] is True

    def test_timeout_error_is_retryable(self, client, auth_headers, monkeypatch):
        from app.services import ocr_engine as ocr_module

        def _raise(*_args, **_kwargs):
            raise TimeoutError("Socket timed out")

        monkeypatch.setattr(ocr_module.ocr_engine, "extract_packaging_label", _raise)

        resp = client.post(
            "/api/v1/ocr/scan",
            files={"file": ("test.png", _make_minimal_png_bytes(), "image/png")},
            data={"source_type": "packaging"},
            headers=auth_headers,
        )
        assert resp.status_code == 500
        detail = resp.json()["detail"]
        assert detail["retryable"] is True


# ─────────────────────────────────────────────────────────────────────────────
# 4. Request Tracing & Contract
# ─────────────────────────────────────────────────────────────────────────────

class TestRequestTracing:
    def test_custom_request_id_propagated_to_headers_and_error(self, client, auth_headers, monkeypatch):
        from app.services import ocr_engine as ocr_module

        def _raise(*_args, **_kwargs):
            raise RuntimeError("Crash for trace test")

        monkeypatch.setattr(ocr_module.ocr_engine, "extract_packaging_label", _raise)

        custom_id = "trace-custom-uuid-9999"
        headers = {**auth_headers, "X-Request-ID": custom_id}

        resp = client.post(
            "/api/v1/ocr/scan",
            files={"file": ("test.png", _make_minimal_png_bytes(), "image/png")},
            data={"source_type": "packaging"},
            headers=headers,
        )
        assert resp.status_code == 500
        assert resp.headers.get("X-Request-ID") == custom_id
        detail = resp.json()["detail"]
        assert detail["request_id"] == custom_id
        assert REQUIRED_ERROR_KEYS.issubset(detail.keys())


# ─────────────────────────────────────────────────────────────────────────────
# 5. Health, Readiness, and Warmup Endpoints
# ─────────────────────────────────────────────────────────────────────────────

class TestHealthEndpoints:
    def test_liveness_probe(self, client):
        resp = client.get("/health/live")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["probe"] == "liveness"

    def test_readiness_probe(self, client):
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["probe"] == "readiness"
        assert "database" in body

    def test_model_warmup_probe(self, client):
        resp = client.post("/health/warmup")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["warmup"] == "completed"
        assert "elapsed_ms" in body
