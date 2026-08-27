"""
Profile Service — Quản lý Hồ sơ Y tế Cá nhân hóa (Stage 9).
Lưu trữ thread-safe theo `user_id` tại backend/app/data/profiles.json.
Tự động tính toán chỉ số BMI.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

from app.schemas.user_profile_schema import (
    UserProfileCreate,
    UserProfileResponse,
    UserProfileUpdate,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PROFILES_FILE = DATA_DIR / "profiles.json"


def calculate_bmi(weight_kg: Optional[float], height_cm: Optional[float]) -> Optional[float]:
    """Tính chỉ số khối cơ thể BMI = weight_kg / (height_m ^ 2). Làm tròn 1 chữ số thập phân."""
    if weight_kg and height_cm and height_cm > 0:
        height_m = height_cm / 100.0
        return round(weight_kg / (height_m * height_m), 1)
    return None


class ProfileService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._profiles: Dict[str, Dict[str, Any]] = {}
        self._load_profiles()

    def _load_profiles(self) -> None:
        """Đọc danh sách profiles từ file JSON (nếu có)."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if PROFILES_FILE.exists():
            try:
                with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                    self._profiles = json.load(f)
            except Exception as exc:
                logger.warning("Không thể đọc profiles.json, khởi tạo bộ nhớ trống: %s", exc)
                self._profiles = {}

    def _save_profiles(self) -> None:
        """Ghi danh sách profiles vào file JSON thread-safe."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(PROFILES_FILE, "w", encoding="utf-8") as f:
                json.dump(self._profiles, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.error("Lỗi khi ghi profiles.json: %s", exc)

    def get_profile(self, user_id: str) -> Optional[UserProfileResponse]:
        """Lấy hồ sơ y tế theo ID người dùng."""
        with self._lock:
            p = self._profiles.get(user_id)
            if not p:
                return None
            return UserProfileResponse(
                user_id=p["user_id"],
                age=p["age"],
                birth_year=p.get("birth_year"),
                gender=p.get("gender"),
                weight_kg=p.get("weight_kg"),
                height_cm=p.get("height_cm"),
                bmi=p.get("bmi"),
                conditions=p.get("conditions", []),
                allergies=p.get("allergies", []),
                updated_at=p["updated_at"],
            )

    def upsert_profile(self, user_id: str, data: UserProfileCreate) -> UserProfileResponse:
        """Tạo mới hoặc ghi đè hồ sơ y tế cho người dùng."""
        bmi = calculate_bmi(data.weight_kg, data.height_cm)
        updated_at = datetime.now(timezone.utc).isoformat()

        record = {
            "user_id": user_id,
            "age": data.age,
            "birth_year": data.birth_year,
            "gender": data.gender,
            "weight_kg": data.weight_kg,
            "height_cm": data.height_cm,
            "bmi": bmi,
            "conditions": data.conditions,
            "allergies": data.allergies,
            "updated_at": updated_at,
        }

        with self._lock:
            self._profiles[user_id] = record
            self._save_profiles()

        return UserProfileResponse(**record)

    def update_profile(self, user_id: str, data: UserProfileUpdate) -> UserProfileResponse:
        """Cập nhật một phần hồ sơ y tế của người dùng."""
        with self._lock:
            existing = self._profiles.get(user_id)
            if not existing:
                # Nếu chưa có -> tạo mới với giá trị mặc định
                create_data = UserProfileCreate(
                    age=data.age if data.age is not None else 30,
                    birth_year=data.birth_year,
                    gender=data.gender,
                    weight_kg=data.weight_kg,
                    height_cm=data.height_cm,
                    conditions=data.conditions if data.conditions is not None else [],
                    allergies=data.allergies if data.allergies is not None else [],
                )
                return self.upsert_profile(user_id, create_data)

            # Cập nhật các trường được truyền lên
            if data.age is not None:
                existing["age"] = data.age
            if data.birth_year is not None:
                existing["birth_year"] = data.birth_year
            if data.gender is not None:
                existing["gender"] = data.gender
            if data.weight_kg is not None:
                existing["weight_kg"] = data.weight_kg
            if data.height_cm is not None:
                existing["height_cm"] = data.height_cm
            if data.conditions is not None:
                existing["conditions"] = data.conditions
            if data.allergies is not None:
                existing["allergies"] = data.allergies

            existing["bmi"] = calculate_bmi(existing.get("weight_kg"), existing.get("height_cm"))
            existing["updated_at"] = datetime.now(timezone.utc).isoformat()

            self._save_profiles()

            return UserProfileResponse(**existing)


profile_service = ProfileService()
