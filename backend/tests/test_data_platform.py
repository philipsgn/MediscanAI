"""
test_data_platform.py

Comprehensive Test Suite for Mediscan AI Data-Centric Platform:
1. Scan Persistence & Lineage Traceability.
2. Data Quality Scoring & Review Queue Triggering.
3. Non-destructive Human Correction (HITL — Zero-Overwrite Rule).
4. Dataset Candidate Lifecycle & Constraints.
5. Dataset Export for Active Learning with Full Lineage.
6. Safe Degradation on DB Failure.
"""

import io
import os
import uuid
from typing import Dict

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image as PILImage

os.environ.setdefault("MEDISCAN_TEST_MODE", "true")

from app.core.limiter import limiter
from app.core.versioning import (
    CLINICAL_MODEL_VERSION,
    CLINICAL_RULES_VERSION,
    DEFAULT_DATASET_VERSION,
    NORMALIZATION_VERSION,
    OCR_MODEL_VERSION,
    PIPELINE_VERSION,
    PROMPT_VERSION,
)
from app.main import app
from app.models.data_capture import ScanRecordModel
from app.schemas.data_platform_schema import ScanRecordStatus
from app.services.data_capture_service import data_capture_service
from app.services.data_quality_service import data_quality_service


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures & Helpers
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_limiter():
    try:
        limiter.reset()
    except Exception:
        pass


def _make_minimal_png_bytes() -> bytes:
    """Tạo file PNG 1x1 pixel hợp lệ."""
    import base64
    b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
    return base64.b64decode(b64)


async def _create_authenticated_user(client: AsyncClient) -> Dict[str, str]:
    """Helper đăng ký user và trả về headers kèm Bearer token và user_id."""
    try:
        limiter.reset()
    except Exception:
        pass
    unique = uuid.uuid4().hex[:8]
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"dataplatform_{unique}@mediscan.ai",
            "username": f"dataplatform_{unique}",
            "password": "DataPlatform@1234",
            "full_name": "Data Platform Reviewer",
        },
    )
    assert resp.status_code == 201, f"Register failed: {resp.text}"
    token = resp.json()["accessToken"]
    user_id = resp.json()["user"]["id"]
    return {
        "Authorization": f"Bearer {token}",
        "user_id": user_id,
        "token": token,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. Data Quality Service Unit Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDataQualityService:
    def test_clean_high_confidence_is_processed(self):
        raw_ocr = [{"text": "PARACETAMOL 500mg", "confidence": 0.95, "box": [10, 10, 100, 30]}]
        mapped_drugs = [{
            "brand_name": "PARACETAMOL",
            "active_ingredient": "Paracetamol",
            "is_verified": True,
            "match_method": "exact",
            "strength": "500mg",
            "strength_mismatch_warning": None,
        }]
        score, flags, status = data_quality_service.evaluate_scan(raw_ocr, mapped_drugs)
        assert score >= 0.85
        assert len(flags) == 0
        assert status == ScanRecordStatus.PROCESSED

    def test_low_ocr_confidence_triggers_review(self):
        raw_ocr = [{"text": "Blurry text", "confidence": 0.55, "box": [0, 0, 10, 10]}]
        mapped_drugs = [{"brand_name": "Blurry text", "is_verified": False, "match_method": None}]
        score, flags, status = data_quality_service.evaluate_scan(raw_ocr, mapped_drugs)
        assert "LOW_OCR_CONFIDENCE" in flags
        assert "UNVERIFIED_DRUG_MATCH" in flags
        assert status == ScanRecordStatus.REVIEW_REQUIRED

    def test_strength_mismatch_triggers_review(self):
        raw_ocr = [{"text": "Panadol 1000mg", "confidence": 0.92, "box": [0, 0, 10, 10]}]
        mapped_drugs = [{
            "brand_name": "Panadol",
            "active_ingredient": "Paracetamol",
            "is_verified": True,
            "match_method": "exact",
            "strength_mismatch_warning": "Hàm lượng OCR (1000mg) khác biệt với DB (500mg)",
        }]
        score, flags, status = data_quality_service.evaluate_scan(raw_ocr, mapped_drugs)
        assert "STRENGTH_MISMATCH" in flags
        assert status == ScanRecordStatus.REVIEW_REQUIRED


# ─────────────────────────────────────────────────────────────────────────────
# 2. Integration Tests: Scan Persistence & Lineage in /ocr/scan
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ocr_scan_persists_scan_record_and_returns_scan_id():
    """Verify endpoint /ocr/scan tự động lưu scan_records và trả về scan_id trong response."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth = await _create_authenticated_user(client)
        headers = {"Authorization": auth["Authorization"]}

        # Onboard user
        await client.post(
            "/api/v1/profile",
            json={"age": 30, "conditions": [], "allergies": []},
            headers=headers,
        )

        png_bytes = _make_minimal_png_bytes()
        resp = await client.post(
            "/api/v1/ocr/scan",
            files={"file": ("test_scan.png", png_bytes, "image/png")},
            data={"source_type": "packaging", "run_clinical": "false"},
            headers={**headers, "X-Request-ID": "req-lineage-test-1"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "scanId" in body
        assert body["scanId"] is not None
        assert body["requestId"] == "req-lineage-test-1"

        # Kiểm tra chi tiết scan record qua API Review
        review_resp = await client.get(f"/api/v1/data/reviews/{body['scanId']}", headers=headers)
        assert review_resp.status_code == 200
        detail = review_resp.json()
        assert detail["scanId"] == body["scanId"]
        assert detail["requestId"] == "req-lineage-test-1"
        assert detail["imageRef"].startswith("sha256:")
        assert detail["versionMetadata"]["pipelineVersion"] == PIPELINE_VERSION
        assert detail["versionMetadata"]["ocrModelVersion"] == OCR_MODEL_VERSION
        assert detail["versionMetadata"]["normalizationVersion"] == NORMALIZATION_VERSION
        assert detail["versionMetadata"]["clinicalRulesVersion"] == CLINICAL_RULES_VERSION


# ─────────────────────────────────────────────────────────────────────────────
# 3. Review Queue, Human Correction (HITL) & Zero-Overwrite Verification
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_human_correction_saves_payload_without_overwriting_raw_ai():
    """
    KIỂM THỬ QUY TẮC BẢO VỆ BẤT BIẾN:
    Submit correction từ Reviewer phải lưu vào corrected_payload,
    TUYỆT ĐỐI KHÔNG ghi đè raw_ocr_result hay normalized_result gốc.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth = await _create_authenticated_user(client)
        headers = {"Authorization": auth["Authorization"]}

        # Onboard user
        await client.post(
            "/api/v1/profile",
            json={"age": 30, "conditions": [], "allergies": []},
            headers=headers,
        )

        png_bytes = _make_minimal_png_bytes()
        scan_resp = await client.post(
            "/api/v1/ocr/scan",
            files={"file": ("test_hitl.png", png_bytes, "image/png")},
            data={"source_type": "packaging", "run_clinical": "false"},
            headers=headers,
        )
        scan_id = scan_resp.json()["scanId"]

        # Lấy bản ghi ban đầu
        initial_detail = (await client.get(f"/api/v1/data/reviews/{scan_id}", headers=headers)).json()
        original_raw_ocr = initial_detail["rawOcrResult"]
        original_normalized = initial_detail["normalizedResult"]

        # Reviewer thực hiện hiệu đính HITL
        correct_req = {
            "decision": "ACCEPTED",
            "review_notes": "Đã đối chiếu vỏ hộp thực tế: Panadol Extra 500mg/65mg",
            "corrected_drugs": [
                {
                    "brand_name": "Panadol Extra",
                    "active_ingredient": "Paracetamol + Caffeine",
                    "strength": "500mg + 65mg",
                    "dosage_instruction": "Uống 1-2 viên mỗi 4-6 giờ",
                    "notes": "Liều tối đa 8 viên/ngày",
                }
            ],
        }

        correct_res = await client.post(
            f"/api/v1/data/reviews/{scan_id}/correct",
            json=correct_req,
            headers=headers,
        )
        assert correct_res.status_code == 200
        correct_body = correct_res.json()
        assert correct_body["status"] == "ACCEPTED"
        assert correct_body["correctedDrugsCount"] == 1

        # Lấy lại chi tiết sau khi sửa
        updated_detail = (await client.get(f"/api/v1/data/reviews/{scan_id}", headers=headers)).json()
        assert updated_detail["status"] == "ACCEPTED"
        assert updated_detail["reviewedBy"] == auth["user_id"]
        assert updated_detail["reviewNotes"] == "Đã đối chiếu vỏ hộp thực tế: Panadol Extra 500mg/65mg"

        # BẢO VỆ RAW AI ARTIFACTS:
        assert updated_detail["rawOcrResult"] == original_raw_ocr
        assert updated_detail["normalizedResult"] == original_normalized

        # Dữ liệu sửa nằm riêng trong corrected_payload:
        assert updated_detail["correctedPayload"] is not None
        assert len(updated_detail["correctedPayload"]["corrected_drugs"]) == 1
        assert updated_detail["correctedPayload"]["corrected_drugs"][0]["brand_name"] == "Panadol Extra"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Review Queue Filtering & Pagination
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_review_queue_listing_and_filtering():
    """Verify endpoint GET /api/v1/data/reviews phân trang và lọc theo trạng thái."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth = await _create_authenticated_user(client)
        headers = {"Authorization": auth["Authorization"]}

        resp = await client.get("/api/v1/data/reviews?limit=10&offset=0", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "total" in body
        assert "items" in body
        assert isinstance(body["items"], list)
        assert body["limit"] == 10
        assert body["offset"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# 5. Dataset Candidate Lifecycle & Active Learning Export
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dataset_candidate_lifecycle_and_export():
    """
    Kiểm thử luồng Dataset Candidate:
    1. Scan chưa review không thể mark candidate (400 rejection).
    2. Scan đã ACCEPTED được mark candidate thành công.
    3. Export dataset trả về cặp Ground Truth vs Raw OCR kèm Model Lineage.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth = await _create_authenticated_user(client)
        headers = {"Authorization": auth["Authorization"]}

        # Onboard user
        await client.post(
            "/api/v1/profile",
            json={"age": 25, "conditions": [], "allergies": []},
            headers=headers,
        )

        png_bytes = _make_minimal_png_bytes()
        scan_resp = await client.post(
            "/api/v1/ocr/scan",
            files={"file": ("candidate_test.png", png_bytes, "image/png")},
            data={"source_type": "prescription", "run_clinical": "false"},
            headers=headers,
        )
        scan_id = scan_resp.json()["scanId"]

        # 1. Thử đánh dấu candidate khi chưa Review (trạng thái REVIEW_REQUIRED / PROCESSED)
        # Nếu scan có status REVIEW_REQUIRED/PROCESSED, không được phép tạo Ground Truth
        # Cho scan này vào trạng thái REJECTED trước
        await client.post(
            f"/api/v1/data/reviews/{scan_id}/correct",
            json={"decision": "REJECTED", "review_notes": "Ảnh quá mờ", "corrected_drugs": []},
            headers=headers,
        )
        bad_candidate_resp = await client.post(
            f"/api/v1/data/reviews/{scan_id}/candidate",
            json={"dataset_version": "mediscan-v1.0"},
            headers=headers,
        )
        assert bad_candidate_resp.status_code == 400
        assert "INVALID_DATASET_CANDIDATE_TRANSITION" in bad_candidate_resp.json()["detail"]["error_code"]

        # 2. Reviewer duyệt hợp lệ (ACCEPTED)
        await client.post(
            f"/api/v1/data/reviews/{scan_id}/correct",
            json={
                "decision": "ACCEPTED",
                "review_notes": "Chấp thuận toa thuốc chuẩn",
                "corrected_drugs": [
                    {
                        "brand_name": "Augmentin 1g",
                        "active_ingredient": "Amoxicillin + Clavulanic acid",
                        "strength": "1000mg",
                        "dosage_instruction": "Uống 1 viên x 2 lần/ngày",
                    }
                ],
            },
            headers=headers,
        )

        # 3. Đánh dấu dataset candidate
        good_candidate_resp = await client.post(
            f"/api/v1/data/reviews/{scan_id}/candidate",
            json={"dataset_version": "mediscan-active-learning-v1", "dataset_tag": "hard_prescription_cases"},
            headers=headers,
        )
        assert good_candidate_resp.status_code == 200
        assert good_candidate_resp.json()["isDatasetCandidate"] is True
        assert good_candidate_resp.json()["datasetVersion"] == "mediscan-active-learning-v1"

        # 4. Xuất dataset Active Learning
        export_resp = await client.get(
            "/api/v1/data/datasets/export?dataset_version=mediscan-active-learning-v1",
            headers=headers,
        )
        assert export_resp.status_code == 200
        export_body = export_resp.json()
        assert export_body["datasetVersion"] == "mediscan-active-learning-v1"
        assert export_body["totalSamples"] >= 1

        sample = next((s for s in export_body["samples"] if s["scanId"] == scan_id), None)
        assert sample is not None
        assert sample["lineage"]["pipelineVersion"] == PIPELINE_VERSION
        assert sample["lineage"]["ocrModelVersion"] == OCR_MODEL_VERSION
        assert len(sample["groundTruthDrugs"]) == 1
        assert sample["groundTruthDrugs"][0]["brandName"] == "Augmentin 1g"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Safe Degradation Test
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_safe_degradation_when_data_capture_fails(monkeypatch):
    """
    Verify cơ chế Safe Degradation:
    Nếu DataCaptureService.capture_scan gặp sự cố DB, endpoint /ocr/scan vẫn
    hoàn thành thành công 200 và trả kết quả scan cho User (scan_id = None).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth = await _create_authenticated_user(client)
        headers = {"Authorization": auth["Authorization"]}

        # Onboard user
        await client.post(
            "/api/v1/profile",
            json={"age": 40, "conditions": [], "allergies": []},
            headers=headers,
        )

        async def _mock_capture_fail(*_args, **_kwargs):
            return None  # Giả lập capture bị lỗi và degrade trả về None

        monkeypatch.setattr(data_capture_service, "capture_scan", _mock_capture_fail)

        png_bytes = _make_minimal_png_bytes()
        resp = await client.post(
            "/api/v1/ocr/scan",
            files={"file": ("degrade_test.png", png_bytes, "image/png")},
            data={"source_type": "packaging", "run_clinical": "false"},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["scanId"] is None  # Degraded safely
        assert body["sourceType"] == "packaging"
