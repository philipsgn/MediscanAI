"""
Pydantic Schemas cho Medication History, Cabinet & Smart Reminders (Stage 10).
Đồng bộ 100% Data Contract với Frontend DTOs.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


# ══════════════════════════════════════════════════════════════════════════════
# 1. USER MEDICATIONS (CABINET) SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class UserMedicationCreate(BaseModel):
    brand_name: str = Field(..., min_length=1, max_length=255, description="Tên biệt dược/thương mại")
    active_ingredient: Optional[str] = Field(None, max_length=255, description="Hoạt chất chính")
    strength: Optional[str] = Field(None, max_length=100, description="Hàm lượng (VD: 500mg)")
    dosage_instruction: Optional[str] = Field(None, max_length=255, description="Hướng dẫn liều dùng")
    duration_days: Optional[int] = Field(None, ge=1, le=365, description="Số ngày dùng thuốc")
    is_active: bool = Field(True, description="Trạng thái đang sử dụng")
    notes: Optional[str] = Field(None, description="Ghi chú thêm")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class UserMedicationUpdate(BaseModel):
    brand_name: Optional[str] = Field(None, min_length=1, max_length=255)
    active_ingredient: Optional[str] = Field(None, max_length=255)
    strength: Optional[str] = Field(None, max_length=100)
    dosage_instruction: Optional[str] = Field(None, max_length=255)
    duration_days: Optional[int] = Field(None, ge=1, le=365)
    is_active: Optional[bool] = Field(None)
    notes: Optional[str] = Field(None)

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class UserMedicationResponse(BaseModel):
    id: str = Field(..., description="ID thuốc trong Tủ thuốc")
    user_id: str = Field(..., description="ID chủ sở hữu")
    brand_name: str = Field(..., description="Tên thuốc")
    active_ingredient: Optional[str] = Field(None, description="Hoạt chất")
    strength: Optional[str] = Field(None, description="Hàm lượng")
    dosage_instruction: Optional[str] = Field(None, description="Liều dùng")
    duration_days: Optional[int] = Field(None, description="Số ngày dùng")
    is_active: bool = Field(..., description="Trạng thái đang dùng")
    notes: Optional[str] = Field(None, description="Ghi chú")
    created_at: str = Field(..., description="Thời gian thêm")
    updated_at: str = Field(..., description="Thời gian cập nhật")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class PaginatedMedicationsResponse(BaseModel):
    items: List[UserMedicationResponse] = Field(default=[], description="Danh sách thuốc")
    total: int = Field(0, description="Tổng số bản ghi")
    limit: int = Field(50, description="Số lượng bản ghi trên một trang")
    offset: int = Field(0, description="Vị trí bắt đầu")
    has_more: bool = Field(False, description="Còn dữ liệu ở trang tiếp theo không")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


# ══════════════════════════════════════════════════════════════════════════════
# 2. SCAN & EVALUATION HISTORY SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class ScanHistoryCreate(BaseModel):
    """Schema nội bộ (Internal write) lưu snapshot đánh giá lâm sàng."""
    source_type: str = Field(..., description="Nguồn trích xuất ('prescription' | 'packaging' | 'manual')")
    drug_names: List[str] = Field(..., description="Danh sách tên các thuốc trong phiên scan")
    highest_severity: str = Field("NONE", description="Mức độ cảnh báo cao nhất ('HIGH' | 'MEDIUM' | 'LOW' | 'NONE')")
    summary: Optional[str] = Field(None, description="Tóm tắt kết quả đánh giá")
    raw_payload: Optional[Dict[str, Any]] = Field(None, description="Snapshot kết quả lâm sàng (Tuyệt đối không lưu ảnh)")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class ScanHistoryResponse(BaseModel):
    id: str = Field(..., description="ID định danh lịch sử phiên scan")
    user_id: str = Field(..., description="ID tài khoản sở hữu")
    scanned_at: str = Field(..., description="Thời gian thực hiện (ISO 8601 string)")
    source_type: str = Field(..., description="Nguồn trích xuất")
    drug_names: List[str] = Field(..., description="Danh sách tên các thuốc")
    highest_severity: str = Field(..., description="Mức độ cảnh báo cao nhất")
    summary: Optional[str] = Field(None, description="Tóm tắt kết quả đánh giá")
    raw_payload: Optional[Dict[str, Any]] = Field(None, description="Snapshot kết quả lâm sàng chi tiết")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class PaginatedScanHistoryResponse(BaseModel):
    items: List[ScanHistoryResponse] = Field(default=[], description="Danh sách lịch sử các phiên đánh giá")
    total: int = Field(0, description="Tổng số bản ghi")
    limit: int = Field(50, description="Số lượng bản ghi trên một trang")
    offset: int = Field(0, description="Vị trí bắt đầu")
    has_more: bool = Field(False, description="Còn dữ liệu không")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


# ══════════════════════════════════════════════════════════════════════════════
# 3. SMART DOSAGE REMINDERS SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class ReminderCreate(BaseModel):
    medication_id: Optional[str] = Field(None, description="ID thuốc trong Tủ thuốc liên kết (nếu có)")
    drug_name: str = Field(..., min_length=1, max_length=255, description="Tên thuốc cần nhắc nhở")
    dosage_instruction: Optional[str] = Field(None, max_length=255, description="Hướng dẫn liều dùng")
    time_of_day: str = Field(..., description="Buổi trong ngày ('morning' | 'noon' | 'afternoon' | 'evening')")
    reminder_time: str = Field(
        "08:00",
        pattern=r"^([01]\d|2[0-3]):([0-5]\d)$",
        description="Giờ nhắc nhở định dạng HH:MM 24h",
    )
    is_active: bool = Field(True, description="Trạng thái bật/tắt nhắc nhở")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class ReminderUpdate(BaseModel):
    medication_id: Optional[str] = Field(None, description="ID thuốc trong Tủ thuốc liên kết")
    drug_name: Optional[str] = Field(None, min_length=1, max_length=255)
    dosage_instruction: Optional[str] = Field(None, max_length=255)
    time_of_day: Optional[str] = Field(None)
    reminder_time: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):([0-5]\d)$")
    is_active: Optional[bool] = Field(None)

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class ReminderLogCreate(BaseModel):
    status: str = Field(..., pattern=r"^(taken|skipped)$", description="Trạng thái ('taken' | 'skipped')")
    notes: Optional[str] = Field(None, max_length=500, description="Ghi chú thêm")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class ReminderLogItem(BaseModel):
    log_id: str = Field(..., description="ID nhật ký uống")
    status: str = Field(..., description="Trạng thái uống ('taken' | 'skipped')")
    timestamp: str = Field(..., description="Thời gian ghi nhận")
    notes: Optional[str] = Field(None, description="Ghi chú thêm")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class ReminderResponse(BaseModel):
    id: str = Field(..., description="ID nhắc nhở")
    user_id: str = Field(..., description="ID tài khoản sở hữu")
    medication_id: Optional[str] = Field(None, description="ID thuốc liên kết trong Tủ thuốc")
    drug_name: str = Field(..., description="Tên thuốc")
    dosage_instruction: Optional[str] = Field(None, description="Liều dùng")
    time_of_day: str = Field(..., description="Buổi trong ngày")
    reminder_time: str = Field(..., description="Giờ nhắc nhở")
    is_active: bool = Field(..., description="Trạng thái bật/tắt")
    created_at: str = Field(..., description="Thời gian tạo")
    logs: List[ReminderLogItem] = Field(default=[], description="Nhật ký các lần uống thuốc")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class AdherenceStats(BaseModel):
    total_reminders: int = Field(0, description="Tổng số nhắc nhở đang có")
    today_taken_count: int = Field(0, description="Số cữ đã uống trong ngày hôm nay")
    today_skipped_count: int = Field(0, description="Số cữ đã bỏ qua trong ngày hôm nay")
    today_total_scheduled: int = Field(0, description="Tổng số cữ cần uống trong ngày hôm nay (active)")
    today_adherence_rate: float = Field(0.0, description="Tỉ lệ tuân thủ trong ngày hôm nay % (0.0 -> 100.0)")
    taken_count: int = Field(0, description="Tổng số lần đã đánh dấu uống thuốc (cả quá trình)")
    skipped_count: int = Field(0, description="Tổng số lần bỏ qua (cả quá trình)")
    adherence_rate: float = Field(0.0, description="Tỉ lệ tuân thủ của cả quá trình % (0.0 -> 100.0)")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class PaginatedRemindersOverviewResponse(BaseModel):
    items: List[ReminderResponse] = Field(default=[], description="Danh sách nhắc nhở")
    total: int = Field(0, description="Tổng số bản ghi")
    limit: int = Field(50, description="Số lượng bản ghi trên một trang")
    offset: int = Field(0, description="Vị trí bắt đầu")
    has_more: bool = Field(False, description="Còn dữ liệu không")
    stats: AdherenceStats = Field(default_factory=AdherenceStats, description="Thống kê tuân thủ điều trị")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
