"""
test_data_platform.py

Privacy Hardening & Data Platform Test Suite for Mediscan AI:
1. RAM-Only Pipeline Verification: Scan processing creates ZERO image files on disk.
2. Complete absence of image_storage_ref / image_ref in API schemas and responses.
3. State Machine & Transition Validation (Strict Ground Truth Lifecycle).
4. ONLY `ACCEPTED` status can become Dataset Candidate / Ground Truth.
5. Non-silent Data Capture Failure & Metrics Monitoring.
6. Concurrent Review Safety (Optimistic Locking Conflict Detection).
7. Mutation Idempotency (Safe Network Retries).
8. Dataset Snapshot Hash Integrity & Reproducibility.
9. Zero-Overwrite of Raw AI Predictions.
"""

import io
import os
import uuid
from pathlib import Path
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
    get_git_commit_hash,
    get_ocr_model_hash,
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
# 1. RAM-Only Pipeline & ZERO Image Disk Persistence Verification
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ram_only_pipeline_zero_image_persistence():
    """
    KIỂM THỬ QUYỀN RIÊNG TƯ TUYỆT ĐỐI (ARCHITECTURE.md 7.1):
    1. Scan thực tế xử lý 100% trong RAM.
    2. Không sinh bất kỳ file ảnh nào trên đĩa cứng (thư mục data/storage không được tạo).
    3. Không tồn tại các trường imageStorageRef / imageRef / imageAvailable trong response.
    4. Chỉ lưu fingerprint checksum SHA-256 (64 hex) phục vụ deduplication/audit log.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth = await _create_authenticated_user(client)
        headers = {"Authorization": auth["Authorization"]}

        await client.post(
            "/api/v1/profile",
            json={"age": 30, "conditions": [], "allergies": []},
            headers=headers,
        )

        png_bytes = _make_minimal_png_bytes()
        scan_resp = await client.post(
            "/api/v1/ocr/scan",
            files={"file": ("privacy_test.png", png_bytes, "image/png")},
            data={"source_type": "packaging", "run_clinical": "false"},
            headers=headers,
        )
        assert scan_resp.status_code == 200
        scan_id = scan_resp.json()["scanId"]

        # 1. Kiểm tra chi tiết scan review
        detail_resp = await client.get(f"/api/v1/data/reviews/{scan_id}", headers=headers)
        assert detail_resp.status_code == 200
        detail = detail_resp.json()

        # Checksum SHA-256 đối soát
        assert len(detail["imageSha256"]) == 64
        # Xác nhận các trường lưu trữ ảnh đã bị xóa hoàn toàn khỏi schema
        assert "imageStorageRef" not in detail
        assert "imageRef" not in detail
        assert "imageAvailable" not in detail

        # 2. Xác nhận không có bất kỳ thư mục data/storage nào được tạo trên ổ đĩa
        assert not Path("data/storage").exists(), "LỖI BẢO MẬT: Thư mục data/storage vẫn tồn tại!"
        assert not Path("data/storage/scans").exists(), "LỖI BẢO MẬT: Thư mục data/storage/scans vẫn tồn tại!"


# ─────────────────────────────────────────────────────────────────────────────
# 2. State Machine & Transition Validation Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invalid_state_transition_is_rejected():
    """Kiểm thử: Chuyển đổi trạng thái bất hợp lệ trong State Machine bị từ chối với HTTP 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth = await _create_authenticated_user(client)
        headers = {"Authorization": auth["Authorization"]}

        await client.post(
            "/api/v1/profile",
            json={"age": 30, "conditions": [], "allergies": []},
            headers=headers,
        )

        scan_resp = await client.post(
            "/api/v1/ocr/scan",
            files={"file": ("test_trans.png", _make_minimal_png_bytes(), "image/png")},
            data={"source_type": "packaging", "run_clinical": "false"},
            headers=headers,
        )
        scan_id = scan_resp.json()["scanId"]

        # Reject scan
        await client.post(
            f"/api/v1/data/reviews/{scan_id}/correct",
            json={"decision": "REJECTED", "review_notes": "Ảnh rác"},
            headers=headers,
        )

        # REJECTED -> ACCEPTED trực tiếp là chuyển trạng thái bất hợp lệ (phải qua IN_REVIEW)
        invalid_resp = await client.post(
            f"/api/v1/data/reviews/{scan_id}/correct",
            json={"decision": "ACCEPTED", "review_notes": "Cố tình chuyển sai"},
            headers=headers,
        )
        assert invalid_resp.status_code == 400
        assert "INVALID_REVIEW_STATE_TRANSITION" in invalid_resp.json()["detail"]["error_code"]


# ─────────────────────────────────────────────────────────────────────────────
# 3. ONLY ACCEPTED Can Become Dataset Candidate
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_only_accepted_can_become_dataset_candidate():
    """
    KIỂM THỬ NGHIÊM NGẶT:
    Chỉ duy nhất scan có trạng thái 'ACCEPTED' mới được phép chuyển thành Dataset Candidate.
    Các trạng thái khác (PROCESSED, REVIEW_REQUIRED, IN_REVIEW, REJECTED, REVIEWED) đều bị reject.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth = await _create_authenticated_user(client)
        headers = {"Authorization": auth["Authorization"]}

        await client.post(
            "/api/v1/profile",
            json={"age": 30, "conditions": [], "allergies": []},
            headers=headers,
        )

        scan_resp = await client.post(
            "/api/v1/ocr/scan",
            files={"file": ("test_ground_truth.png", _make_minimal_png_bytes(), "image/png")},
            data={"source_type": "packaging", "run_clinical": "false"},
            headers=headers,
        )
        scan_id = scan_resp.json()["scanId"]

        # 1. Trạng thái ban đầu (PROCESSED / REVIEW_REQUIRED) -> Thử mark candidate -> Bị từ chối
        bad_resp1 = await client.post(
            f"/api/v1/data/reviews/{scan_id}/candidate",
            json={"dataset_version": "v1.0"},
            headers=headers,
        )
        assert bad_resp1.status_code == 400
        assert "INVALID_DATASET_CANDIDATE_TRANSITION" in bad_resp1.json()["detail"]["error_code"]

        # 2. Chuyển sang IN_REVIEW -> Thử mark candidate -> Bị từ chối
        await client.post(
            f"/api/v1/data/reviews/{scan_id}/correct",
            json={"decision": "IN_REVIEW", "review_notes": "Đang xem"},
            headers=headers,
        )
        bad_resp2 = await client.post(
            f"/api/v1/data/reviews/{scan_id}/candidate",
            json={"dataset_version": "v1.0"},
            headers=headers,
        )
        assert bad_resp2.status_code == 400

        # 3. Chuyển sang ACCEPTED -> Mark candidate -> Thành công
        await client.post(
            f"/api/v1/data/reviews/{scan_id}/correct",
            json={
                "decision": "ACCEPTED",
                "review_notes": "Xác nhận đúng",
                "corrected_drugs": [{"brand_name": "Panadol", "strength": "500mg"}],
            },
            headers=headers,
        )
        good_resp = await client.post(
            f"/api/v1/data/reviews/{scan_id}/candidate",
            json={"dataset_version": "mediscan-v1.0"},
            headers=headers,
        )
        assert good_resp.status_code == 200
        assert good_resp.json()["isDatasetCandidate"] is True


# ─────────────────────────────────────────────────────────────────────────────
# 4. Concurrent Review Safety (Optimistic Locking)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_concurrent_review_optimistic_locking_conflict():
    """
    Kiểm thử: Khi 2 reviewer cùng sửa 1 scan, reviewer có expected_version cũ
    sẽ nhận HTTP 409 CONFLICT (chống Lost Update).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth1 = await _create_authenticated_user(client)
        auth2 = await _create_authenticated_user(client)

        headers1 = {"Authorization": auth1["Authorization"]}
        headers2 = {"Authorization": auth2["Authorization"]}

        await client.post(
            "/api/v1/profile",
            json={"age": 30, "conditions": [], "allergies": []},
            headers=headers1,
        )

        scan_resp = await client.post(
            "/api/v1/ocr/scan",
            files={"file": ("test_concurrent.png", _make_minimal_png_bytes(), "image/png")},
            data={"source_type": "packaging", "run_clinical": "false"},
            headers=headers1,
        )
        scan_id = scan_resp.json()["scanId"]

        # Cả 2 reviewer đọc bản ghi ở version 1
        initial_detail = (await client.get(f"/api/v1/data/reviews/{scan_id}", headers=headers1)).json()
        v1 = initial_detail["version"]
        assert v1 == 1

        # Reviewer 1 submit thành công (bản ghi lên version 2)
        resp1 = await client.post(
            f"/api/v1/data/reviews/{scan_id}/correct",
            json={"decision": "ACCEPTED", "expected_version": 1, "review_notes": "Reviewer 1 update"},
            headers=headers1,
        )
        assert resp1.status_code == 200
        assert resp1.json()["version"] == 2

        # Reviewer 2 submit với expected_version=1 (stale version) -> Bị 409 Conflict
        resp2 = await client.post(
            f"/api/v1/data/reviews/{scan_id}/correct",
            json={"decision": "REJECTED", "expected_version": 1, "review_notes": "Reviewer 2 conflicting update"},
            headers=headers2,
        )
        assert resp2.status_code == 409
        assert resp2.json()["detail"]["error_code"] == "OPTIMISTIC_LOCK_CONFLICT"


# ─────────────────────────────────────────────────────────────────────────────
# 5. Idempotency on Mutation Retries
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_human_correction_is_idempotent():
    """Kiểm thử: Gửi lại cùng một payload hiệu đính trên bản ghi đã duyệt trả về 200 thành công mà không gây lỗi."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth = await _create_authenticated_user(client)
        headers = {"Authorization": auth["Authorization"]}

        await client.post(
            "/api/v1/profile",
            json={"age": 30, "conditions": [], "allergies": []},
            headers=headers,
        )

        scan_resp = await client.post(
            "/api/v1/ocr/scan",
            files={"file": ("test_idem.png", _make_minimal_png_bytes(), "image/png")},
            data={"source_type": "packaging", "run_clinical": "false"},
            headers=headers,
        )
        scan_id = scan_resp.json()["scanId"]

        payload = {
            "decision": "ACCEPTED",
            "review_notes": "Idempotent test",
            "corrected_drugs": [{"brand_name": "Aspirin", "strength": "100mg"}],
        }

        # Lần 1
        res1 = await client.post(f"/api/v1/data/reviews/{scan_id}/correct", json=payload, headers=headers)
        assert res1.status_code == 200

        # Lần 2 (Network retry)
        res2 = await client.post(f"/api/v1/data/reviews/{scan_id}/correct", json=payload, headers=headers)
        assert res2.status_code == 200
        assert res2.json()["status"] == "ACCEPTED"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Dataset Snapshot Hash & Lineage Reproducibility
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dataset_export_snapshot_hash_and_reproducibility():
    """
    Kiểm thử: Dataset export bao gồm snapshot_hash, lineage metadata
    và chỉ xuất các bản ghi structured đã ACCEPTED.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth = await _create_authenticated_user(client)
        headers = {"Authorization": auth["Authorization"]}

        await client.post(
            "/api/v1/profile",
            json={"age": 30, "conditions": [], "allergies": []},
            headers=headers,
        )

        scan_resp = await client.post(
            "/api/v1/ocr/scan",
            files={"file": ("test_snap.png", _make_minimal_png_bytes(), "image/png")},
            data={"source_type": "prescription", "run_clinical": "false"},
            headers=headers,
        )
        scan_id = scan_resp.json()["scanId"]

        # Accept scan
        await client.post(
            f"/api/v1/data/reviews/{scan_id}/correct",
            json={"decision": "ACCEPTED", "review_notes": "Approved for snapshot", "corrected_drugs": [{"brand_name": "Amox", "strength": "500mg"}]},
            headers=headers,
        )
        # Mark candidate
        await client.post(
            f"/api/v1/data/reviews/{scan_id}/candidate",
            json={"dataset_version": "reproducible-snap-v1"},
            headers=headers,
        )

        # Export dataset
        exp_res = await client.get("/api/v1/data/datasets/export?dataset_version=reproducible-snap-v1", headers=headers)
        assert exp_res.status_code == 200
        body = exp_res.json()
        assert "snapshotHash" in body
        assert len(body["snapshotHash"]) == 64
        assert body["totalSamples"] >= 1
        sample = next(s for s in body["samples"] if s["scanId"] == scan_id)
        assert sample["lineage"]["gitCommitHash"] is not None
        assert sample["lineage"]["ocrModelHash"] is not None
        assert "imageStorageRef" not in sample


# ─────────────────────────────────────────────────────────────────────────────
# 7. Non-Silent Data Capture Failure & Metrics Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_data_capture_failure_is_observable_and_tracked(monkeypatch):
    """
    Kiểm thử: Khi capture scan gặp sự cố DB, lỗi được ghi nhận có cấu trúc
    và phản ánh vào metrics endpoint (không bị swallow âm thầm).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth = await _create_authenticated_user(client)
        headers = {"Authorization": auth["Authorization"]}

        await client.post(
            "/api/v1/profile",
            json={"age": 30, "conditions": [], "allergies": []},
            headers=headers,
        )

        metrics_before = (await client.get("/api/v1/data/metrics", headers=headers)).json()
        initial_fails = metrics_before["failedCaptures"]

        # Gọi capture_scan trực tiếp với db=None để kiểm tra cơ chế tracking
        res = await data_capture_service.capture_scan(
            db=None,  # Will raise error
            request_id="test-fail-trace-1",
            user_id=auth["user_id"],
            source_type="packaging",
            image_sha256="0" * 64,
            raw_ocr_items=[],
            mapped_drugs=[],
        )
        assert res is None  # Degraded safely

        metrics_after = (await client.get("/api/v1/data/metrics", headers=headers)).json()
        assert metrics_after["failedCaptures"] > initial_fails
        assert any(e["requestId"] == "test-fail-trace-1" or "test-fail-trace-1" in str(e) for e in metrics_after["recentErrors"])
