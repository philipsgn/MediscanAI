"""
Unit & Security Integration tests cho Personalized Clinical Health Profile System (Stage 9).
Kiểm thử chi tiết:
1. CRUD endpoints: GET/POST/PUT /profile/me và /profile aliases
2. Unified 6-key Error Contract trên 404 PROFILE_NOT_FOUND
3. Unauthenticated request rejection (401 UNAUTHORIZED)
4. Disabled user rejection (401 USER_INACTIVE)
5. IDOR & Cross-User Data Isolation (User A vs User B)
6. Input validation (age, weight, height ranges)
7. Atomic completion of User.is_profile_completed
"""

import uuid
from typing import Set
import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.session import get_db
from app.main import app
from app.models.user import User

client = TestClient(app)

REQUIRED_ERROR_KEYS: Set[str] = {
    "error_code",
    "message",
    "service",
    "stage",
    "request_id",
    "retryable",
}


def test_profile_full_flow_me_endpoints():
    """Kiểm thử chu trình đầy đủ tạo/truy xuất/cập nhật Profile qua route chuẩn /profile/me."""
    uid = uuid.uuid4().hex[:6]
    reg_payload = {
        "email": f"profile_{uid}@mediscan.ai",
        "username": f"prof_{uid}",
        "password": "SecurePassword123!",
        "fullName": "Bệnh Nhân Model",
    }
    reg_resp = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201
    assert reg_resp.json()["user"]["isProfileCompleted"] is False
    token = reg_resp.json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Lấy profile khi chưa tạo -> 404 Not Found với 6-Key Error Contract
    get_empty = client.get("/api/v1/profile/me", headers=headers)
    assert get_empty.status_code == 404
    detail = get_empty.json()["detail"]
    assert REQUIRED_ERROR_KEYS.issubset(detail.keys())
    assert detail["error_code"] == "PROFILE_NOT_FOUND"
    assert detail["service"] == "profile"
    assert detail["stage"] == "profile_management"

    # 2. Tạo mới Profile qua POST /profile/me -> 200 OK & Tự động tính chỉ số BMI
    # 65 kg, 170 cm -> BMI = 65 / (1.7 * 1.7) = 22.4913... -> làm tròn 22.5
    profile_create = {
        "age": 45,
        "birthYear": 1981,
        "gender": "male",
        "weightKg": 65.0,
        "heightCm": 170.0,
        "conditions": ["Cao huyết áp", "Suy thận"],
        "allergies": ["Dị ứng Penicillin"],
    }
    create_resp = client.post("/api/v1/profile/me", json=profile_create, headers=headers)
    assert create_resp.status_code == 200
    p_data = create_resp.json()
    assert p_data["age"] == 45
    assert p_data["weightKg"] == 65.0
    assert p_data["heightCm"] == 170.0
    assert p_data["bmi"] == 22.5
    assert "Cao huyết áp" in p_data["conditions"]
    assert "Dị ứng Penicillin" in p_data["allergies"]

    # 3. Kiểm tra User.is_profile_completed đã được kích hoạt thành True
    user_me = client.get("/api/v1/auth/me", headers=headers)
    assert user_me.status_code == 200
    assert user_me.json()["isProfileCompleted"] is True

    # 4. Lấy lại profile qua GET /profile/me -> 200 OK
    get_resp = client.get("/api/v1/profile/me", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["bmi"] == 22.5

    # 5. Cập nhật profile qua PUT /profile/me -> 200 OK
    update_payload = {
        "conditions": ["Cao huyết áp", "Suy thận", "Viêm loét dạ dày"],
        "weightKg": 68.0,
    }
    # 68 kg, 170 cm -> 68 / (1.7 * 1.7) = 23.529... -> làm tròn 23.5
    put_resp = client.put("/api/v1/profile/me", json=update_payload, headers=headers)
    assert put_resp.status_code == 200
    updated_data = put_resp.json()
    assert len(updated_data["conditions"]) == 3
    assert updated_data["weightKg"] == 68.0
    assert updated_data["bmi"] == 23.5


def test_profile_root_aliases_backward_compatible():
    """Kiểm thử các route alias POST /profile và PUT /profile tương thích ngược."""
    uid = uuid.uuid4().hex[:6]
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"alias_{uid}@mediscan.ai",
            "username": f"alias_{uid}",
            "password": "SecurePassword123!",
        },
    )
    token = reg_resp.json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = client.post(
        "/api/v1/profile",
        json={"age": 30, "weightKg": 70.0, "heightCm": 175.0},
        headers=headers,
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["age"] == 30

    put_resp = client.put(
        "/api/v1/profile",
        json={"age": 31},
        headers=headers,
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["age"] == 31


def test_profile_unauthenticated_rejected():
    """Mọi request gọi /profile khi chưa có token đều bị từ chối 401."""
    get_res = client.get("/api/v1/profile/me")
    assert get_res.status_code == 401
    assert get_res.json()["detail"]["error_code"] == "UNAUTHORIZED"

    post_res = client.post("/api/v1/profile/me", json={"age": 30})
    assert post_res.status_code == 401

    put_res = client.put("/api/v1/profile/me", json={"age": 30})
    assert put_res.status_code == 401


@pytest.mark.asyncio
async def test_profile_disabled_user_rejected():
    """Tài khoản bị vô hiệu hóa (is_active=False) bị từ chối 401 USER_INACTIVE khi truy cập Profile."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        uid = uuid.uuid4().hex[:6]
        reg_resp = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": f"inactive_prof_{uid}@mediscan.ai",
                "username": f"inact_prof_{uid}",
                "password": "SecurePassword123!",
            },
        )
        token = reg_resp.json()["accessToken"]
        user_id = reg_resp.json()["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        # Vô hiệu hóa user trong Database
        db_gen = app.dependency_overrides[get_db]
        async for session in db_gen():
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            u = result.scalar_one()
            u.is_active = False
            await session.commit()
            break

        # Gọi GET /profile/me -> 401 USER_INACTIVE
        res = await async_client.get("/api/v1/profile/me", headers=headers)
        assert res.status_code == 401
        assert res.json()["detail"]["error_code"] == "USER_INACTIVE"


def test_profile_idor_isolation_cross_user():
    """IDOR Protection: User A và User B tạo profile riêng biệt, chỉ xem được profile của chính mình."""
    # User A
    uid_a = uuid.uuid4().hex[:6]
    resp_a = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"user_a_{uid_a}@mediscan.ai",
            "username": f"user_a_{uid_a}",
            "password": "PasswordA123!",
        },
    )
    token_a = resp_a.json()["accessToken"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    client.post(
        "/api/v1/profile/me",
        json={"age": 25, "conditions": ["Hen suyễn"], "allergies": ["Aspirin"]},
        headers=headers_a,
    )

    # User B
    uid_b = uuid.uuid4().hex[:6]
    resp_b = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"user_b_{uid_b}@mediscan.ai",
            "username": f"user_b_{uid_b}",
            "password": "PasswordB123!",
        },
    )
    token_b = resp_b.json()["accessToken"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    client.post(
        "/api/v1/profile/me",
        json={"age": 60, "conditions": ["Đái tháo đường"], "allergies": ["Penicillin"]},
        headers=headers_b,
    )

    # Verify User A gets Profile A
    get_a = client.get("/api/v1/profile/me", headers=headers_a)
    assert get_a.status_code == 200
    assert get_a.json()["age"] == 25
    assert "Hen suyễn" in get_a.json()["conditions"]
    assert "Đái tháo đường" not in get_a.json()["conditions"]

    # Verify User B gets Profile B
    get_b = client.get("/api/v1/profile/me", headers=headers_b)
    assert get_b.status_code == 200
    assert get_b.json()["age"] == 60
    assert "Đái tháo đường" in get_b.json()["conditions"]
    assert "Hen suyễn" not in get_b.json()["conditions"]


def test_profile_validation_rejects_invalid_inputs():
    """Kiểm thử validation chặn các giá trị phi lý (age <= 0, weight <= 0, height <= 0)."""
    uid = uuid.uuid4().hex[:6]
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"valid_{uid}@mediscan.ai",
            "username": f"valid_{uid}",
            "password": "Password123!",
        },
    )
    token = resp.json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    # age = 0 -> 422
    res_age0 = client.post("/api/v1/profile/me", json={"age": 0}, headers=headers)
    assert res_age0.status_code == 422

    # age = 150 -> 422
    res_age150 = client.post("/api/v1/profile/me", json={"age": 150}, headers=headers)
    assert res_age150.status_code == 422

    # weight_kg = -5.0 -> 422
    res_w = client.post("/api/v1/profile/me", json={"age": 25, "weightKg": -5.0}, headers=headers)
    assert res_w.status_code == 422

    # height_cm = 0.0 -> 422
    res_h = client.post("/api/v1/profile/me", json={"age": 25, "heightCm": 0.0}, headers=headers)
    assert res_h.status_code == 422
