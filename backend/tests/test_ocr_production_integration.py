"""
Unit & Integration Tests for Production PP-OCRv6_tiny Integration (Stage 2).
Kiểm thử:
1. Scan thuần túy không cần login khi run_clinical=False.
2. Từ chối 401 khi run_clinical=True mà không có token xác thực.
3. Từ chối 422 khi user chưa hoàn tất onboarding (chưa có user_profiles trong DB).
4. Tự động lấy UserProfile từ DB qua Auth token khi run_clinical=True và kích hoạt Layer 3/4 chính xác.
5. Regression 4 ảnh benchmark thật qua endpoint /ocr/scan.
"""

from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.limiter import limiter

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "ai" / "benchmark" / "ocr_models" / "sample_images"


@pytest.fixture(autouse=True)
def reset_limiter():
    try:
        limiter.reset()
    except Exception:
        pass



@pytest.mark.asyncio
@pytest.mark.parametrize("run_clinical", ["false", "true"])
async def test_ocr_scan_unauthenticated_rejects_with_401(run_clinical: str):
    """Case 1: Mọi request gọi /ocr/scan khi chưa đăng nhập đều bị chặn 401 UNAUTHORIZED."""
    img_path = SAMPLE_DIR / "vi-thuoc.jpg"
    assert img_path.exists(), f"Không tìm thấy {img_path}"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with open(img_path, "rb") as f:
            files = {"file": ("vi-thuoc.jpg", f.read(), "image/jpeg")}
            data = {"source_type": "packaging", "run_clinical": run_clinical}
            res = await client.post("/api/v1/ocr/scan", files=files, data=data)

        assert res.status_code == 401
        assert "Thiếu Token" in res.json().get("detail", "") or "hết hạn" in res.json().get("detail", "")


@pytest.mark.asyncio
async def test_ocr_scan_authenticated_without_clinical_success():
    """Case 2: User đã đăng nhập gọi /ocr/scan với run_clinical=false -> 200 OK (không cần profile)."""
    img_path = SAMPLE_DIR / "vi-thuoc.jpg"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Đăng ký tài khoản
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "pure_ocr_user@mediscan.ai",
                "username": "pure_ocr_user",
                "password": "Password123!",
                "full_name": "Pure OCR User",
            },
        )
        assert reg_res.status_code == 201
        token = reg_res.json()["accessToken"]

        with open(img_path, "rb") as f:
            files = {"file": ("vi-thuoc.jpg", f.read(), "image/jpeg")}
            data = {"source_type": "packaging", "run_clinical": "false"}
            headers = {"Authorization": f"Bearer {token}"}
            res = await client.post("/api/v1/ocr/scan", files=files, data=data, headers=headers)

        assert res.status_code == 200
        res_data = res.json()
        assert res_data["sourceType"] == "packaging"
        assert len(res_data["rawOcrItems"]) > 0
        assert res_data["clinicalAssessment"] is None


@pytest.mark.asyncio
async def test_ocr_scan_clinical_rejects_incomplete_onboarding():
    """Case 3: User đã đăng nhập nhưng chưa hoàn tất Onboarding -> nhận 422 khi run_clinical=true."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Đăng ký user mới (chưa gọi POST /profile)
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not_onboarded_user_2@mediscan.ai",
                "username": "not_onboarded_2",
                "password": "Password123!",
                "full_name": "Chưa Onboarding",
            },
        )
        assert reg_res.status_code == 201
        token = reg_res.json()["accessToken"]

        img_path = SAMPLE_DIR / "vi-thuoc.jpg"
        with open(img_path, "rb") as f:
            files = {"file": ("vi-thuoc.jpg", f.read(), "image/jpeg")}
            data = {"source_type": "packaging", "run_clinical": "true"}
            headers = {"Authorization": f"Bearer {token}"}
            res = await client.post("/api/v1/ocr/scan", files=files, data=data, headers=headers)

        assert res.status_code == 422
        assert "chưa hoàn tất hồ sơ y tế" in res.json().get("detail", "")


@pytest.mark.asyncio
async def test_ocr_scan_clinical_with_db_profile():
    """Case 4: User đã onboarding (có bệnh nền Suy thận) -> tự động đọc profile từ DB và phân tích lâm sàng."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Đăng ký user
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "onboarded_patient_ocr_2@mediscan.ai",
                "username": "patient_ocr_2",
                "password": "Password123!",
                "full_name": "Bệnh Nhân Đã Onboarding",
            },
        )
        assert reg_res.status_code == 201
        token = reg_res.json()["accessToken"]

        # 2. Hoàn tất Onboarding với bệnh nền "Suy thận"
        headers = {"Authorization": f"Bearer {token}"}
        profile_res = await client.post(
            "/api/v1/profile",
            json={
                "age": 60,
                "gender": "male",
                "conditions": ["Suy thận"],
                "allergies": ["Dị ứng Penicillin"],
            },
            headers=headers,
        )
        assert profile_res.status_code == 200

        # 3. Quét toa thuốc
        img_path = SAMPLE_DIR / "toa-thuoc.jpg"
        with open(img_path, "rb") as f:
            files = {"file": ("toa-thuoc.jpg", f.read(), "image/jpeg")}
            data = {"source_type": "prescription", "run_clinical": "true"}
            res = await client.post("/api/v1/ocr/scan", files=files, data=data, headers=headers)

        assert res.status_code == 200
        res_data = res.json()
        assert res_data["sourceType"] == "prescription"
        assert len(res_data["mappedDrugs"]) > 0


@pytest.mark.asyncio
async def test_ocr_scan_regression_4_benchmark_images():
    """Case 5: Regression toàn bộ 4 ảnh benchmark thật qua /ocr/scan có Header Auth."""
    benchmark_samples = [
        ("hop-thuoc.jpg", "packaging"),
        ("lo-thuoc.png", "packaging"),
        ("vi-thuoc.jpg", "packaging"),
        ("toa-thuoc.jpg", "prescription"),
    ]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Đăng ký 1 user duy nhất cho chuỗi regression 4 ảnh
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "regression_suite_runner@mediscan.ai",
                "username": "reg_runner",
                "password": "Password123!",
                "full_name": "Regression Suite Runner",
            },
        )
        assert reg_res.status_code == 201
        token = reg_res.json()["accessToken"]
        headers = {"Authorization": f"Bearer {token}"}

        for img_name, source_type in benchmark_samples:
            img_path = SAMPLE_DIR / img_name
            assert img_path.exists(), f"Không tìm thấy {img_path}"

            with open(img_path, "rb") as f:
                files = {"file": (img_name, f.read(), "image/jpeg" if not img_name.endswith(".png") else "image/png")}
                data = {"source_type": source_type, "run_clinical": "false"}
                res = await client.post("/api/v1/ocr/scan", files=files, data=data, headers=headers)

            assert res.status_code == 200
            res_data = res.json()
            assert res_data["sourceType"] == source_type
            assert len(res_data["rawOcrItems"]) > 0
            assert res_data["ocrLatencyMs"] < 15000  # SLA limit
            assert res_data["slaExceeded"] is False


