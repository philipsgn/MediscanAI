"""
Unit tests cho Personalized Clinical Health Profile System (Stage 9/10).
Kiểm thử các API: GET /profile/me, POST /profile, PUT /profile, BMI calculation & is_profile_completed lifecycle.
"""

import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_profile_full_flow():
    # 1. Đăng ký tài khoản mới để lấy Access Token
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

    # 2. Lấy profile khi chưa tạo -> 404 Not Found
    get_empty = client.get("/api/v1/profile/me", headers=headers)
    assert get_empty.status_code == 404

    # 3. Tạo mới Profile -> 200 OK & Tự động tính chỉ số BMI
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
    create_resp = client.post("/api/v1/profile", json=profile_create, headers=headers)
    assert create_resp.status_code == 200
    p_data = create_resp.json()
    assert p_data["age"] == 45
    assert p_data["weightKg"] == 65.0
    assert p_data["heightCm"] == 170.0
    assert p_data["bmi"] == 22.5
    assert "Cao huyết áp" in p_data["conditions"]
    assert "Dị ứng Penicillin" in p_data["allergies"]

    # 4. Kiểm tra User.is_profile_completed đã được kích hoạt thành True
    user_me = client.get("/api/v1/auth/me", headers=headers)
    assert user_me.status_code == 200
    assert user_me.json()["isProfileCompleted"] is True

    # 5. Lấy lại profile qua GET /me -> 200 OK
    get_resp = client.get("/api/v1/profile/me", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["bmi"] == 22.5

    # 6. Cập nhật profile qua PUT -> 200 OK
    update_payload = {
        "conditions": ["Cao huyết áp", "Suy thận", "Viêm loét dạ dày"],
        "weightKg": 68.0,
    }
    # 68 kg, 170 cm -> 68 / (1.7 * 1.7) = 23.529... -> làm tròn 23.5
    put_resp = client.put("/api/v1/profile", json=update_payload, headers=headers)
    assert put_resp.status_code == 200
    updated_data = put_resp.json()
    assert len(updated_data["conditions"]) == 3
    assert updated_data["weightKg"] == 68.0
    assert updated_data["bmi"] == 23.5
