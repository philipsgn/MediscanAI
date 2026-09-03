"""
Pydantic Schemas cho Personalized Clinical Health Profile (Stage 9).
Đồng bộ 100% Data Contract với Frontend DTOs (frontend/src/types/medication.ts & profile DTOs).
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class UserProfileCreate(BaseModel):
    age: int = Field(..., ge=1, le=120, description="Tuổi bệnh nhân (1 - 120)")
    birth_year: Optional[int] = Field(None, ge=1900, le=2026, description="Năm sinh")
    gender: Optional[str] = Field(None, description="Giới tính ('male' | 'female' | 'other')")
    weight_kg: Optional[float] = Field(None, gt=0.0, le=300.0, description="Cân nặng (kg, 0 < weight <= 300)")
    height_cm: Optional[float] = Field(None, gt=0.0, le=250.0, description="Chiều cao (cm, 0 < height <= 250)")
    conditions: List[str] = Field(default_factory=list, max_length=50, description="Danh sách bệnh nền")
    allergies: List[str] = Field(default_factory=list, max_length=50, description="Danh sách dị ứng thuốc")
    is_pregnant: Optional[bool] = Field(default=False, description="Đang mang thai")
    is_breastfeeding: Optional[bool] = Field(default=False, description="Đang cho con bú")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class UserProfileUpdate(BaseModel):
    age: Optional[int] = Field(None, ge=1, le=120, description="Tuổi bệnh nhân (1 - 120)")
    birth_year: Optional[int] = Field(None, ge=1900, le=2026, description="Năm sinh")
    gender: Optional[str] = Field(None, description="Giới tính ('male' | 'female' | 'other')")
    weight_kg: Optional[float] = Field(None, gt=0.0, le=300.0, description="Cân nặng (kg, 0 < weight <= 300)")
    height_cm: Optional[float] = Field(None, gt=0.0, le=250.0, description="Chiều cao (cm, 0 < height <= 250)")
    conditions: Optional[List[str]] = Field(None, max_length=50, description="Danh sách bệnh nền")
    allergies: Optional[List[str]] = Field(None, max_length=50, description="Danh sách dị ứng thuốc")
    is_pregnant: Optional[bool] = Field(None, description="Đang mang thai")
    is_breastfeeding: Optional[bool] = Field(None, description="Đang cho con bú")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class UserProfileResponse(BaseModel):
    user_id: str = Field(..., description="ID tài khoản sở hữu hồ sơ")
    age: int = Field(..., description="Tuổi bệnh nhân")
    birth_year: Optional[int] = Field(None, description="Năm sinh")
    gender: Optional[str] = Field(None, description="Giới tính")
    weight_kg: Optional[float] = Field(None, description="Cân nặng (kg)")
    height_cm: Optional[float] = Field(None, description="Chiều cao (cm)")
    bmi: Optional[float] = Field(None, description="Chỉ số khối cơ thể BMI")
    conditions: List[str] = Field(default=[], description="Danh sách bệnh nền")
    allergies: List[str] = Field(default=[], description="Danh sách dị ứng thuốc")
    is_pregnant: Optional[bool] = Field(default=False, description="Đang mang thai")
    is_breastfeeding: Optional[bool] = Field(default=False, description="Đang cho con bú")
    updated_at: str = Field(..., description="Thời gian cập nhật gần nhất (ISO 8601 string)")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
