"""
Unit tests cho Medication History & Smart Reminders System (Stage 10).
Kiểm thử các API: History GET/POST, Reminders GET/POST/PUT/DELETE, Log Status & Adherence calculation.
"""

import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_history_reminders_full_flow():
    # 1. Đăng ký tài khoản mới để nhận token
    uid = uuid.uuid4().hex[:6]
    reg_payload = {
        "email": f"history_{uid}@mediscan.ai",
        "username": f"user_hist_{uid}",
        "password": "SecurePassword123!",
        "fullName": "Bệnh Nhân Stage 10",
    }
    reg_resp = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201
    token = reg_resp.json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Lưu Lịch sử Quét & Đánh giá (POST /api/v1/history) -> 201 Created
    history_create = {
        "sourceType": "prescription",
        "drugNames": ["Panadol Extra 500mg", "Amoxicillin 500mg"],
        "highestSeverity": "MEDIUM",
        "summary": "Phát hiện 1 tương tác nhẹ về cạnh tranh hấp thu",
        "rawPayload": {"alertsCount": 1},
    }
    h_resp = client.post("/api/v1/history", json=history_create, headers=headers)
    assert h_resp.status_code == 201
    h_data = h_resp.json()
    assert h_data["sourceType"] == "prescription"
    assert "Panadol Extra 500mg" in h_data["drugNames"]

    # 3. Lấy lại Lịch sử qua GET /api/v1/history/me -> 200 OK
    get_h_resp = client.get("/api/v1/history/me", headers=headers)
    assert get_h_resp.status_code == 200
    histories = get_h_resp.json()
    assert len(histories) >= 1
    assert histories[0]["highestSeverity"] == "MEDIUM"

    # 4. Tạo Nhắc nhở Uống thuốc (POST /api/v1/reminders) -> 201 Created
    reminder_create = {
        "drugName": "Panadol Extra 500mg",
        "dosageInstruction": "1 viên sau ăn sáng",
        "timeOfDay": "morning",
        "reminderTime": "08:00",
        "isActive": True,
    }
    r_resp = client.post("/api/v1/reminders", json=reminder_create, headers=headers)
    assert r_resp.status_code == 201
    r_data = r_resp.json()
    reminder_id = r_data["id"]
    assert r_data["drugName"] == "Panadol Extra 500mg"
    assert r_data["timeOfDay"] == "morning"

    # 5. Lấy danh sách Reminders & Adherence Stats (GET /api/v1/reminders/me) -> 200 OK
    overview_resp = client.get("/api/v1/reminders/me", headers=headers)
    assert overview_resp.status_code == 200
    ov_data = overview_resp.json()
    assert len(ov_data["reminders"]) == 1
    assert ov_data["stats"]["totalReminders"] == 1
    assert ov_data["stats"]["adherenceRate"] == 0.0

    # 6. Ghi nhận trạng thái 'taken' (Đã uống) -> 200 OK
    log_taken = client.post(
        f"/api/v1/reminders/{reminder_id}/log",
        json={"status": "taken", "notes": "Uống đúng giờ"},
        headers=headers,
    )
    assert log_taken.status_code == 200

    # 7. Ghi nhận trạng thái 'skipped' (Bỏ qua) -> 200 OK
    log_skipped = client.post(
        f"/api/v1/reminders/{reminder_id}/log",
        json={"status": "skipped", "notes": "Quên mang thuốc"},
        headers=headers,
    )
    assert log_skipped.status_code == 200

    # 8. Lấy lại stats -> Tỉ lệ tuân thủ phải là 50.0% (1 taken / 2 total logs)
    ov_resp2 = client.get("/api/v1/reminders/me", headers=headers)
    assert ov_resp2.status_code == 200
    stats2 = ov_resp2.json()["stats"]
    assert stats2["takenCount"] == 1
    assert stats2["skippedCount"] == 1
    assert stats2["adherenceRate"] == 50.0

    # 9. Cập nhật nhắc nhở (PUT /api/v1/reminders/{id}) -> 200 OK
    put_resp = client.put(
        f"/api/v1/reminders/{reminder_id}",
        json={"reminderTime": "08:30", "isActive": False},
        headers=headers,
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["reminderTime"] == "08:30"
    assert put_resp.json()["isActive"] is False

    # 10. Xóa nhắc nhở (DELETE /api/v1/reminders/{id}) -> 200 OK
    del_resp = client.delete(f"/api/v1/reminders/{reminder_id}", headers=headers)
    assert del_resp.status_code == 200
