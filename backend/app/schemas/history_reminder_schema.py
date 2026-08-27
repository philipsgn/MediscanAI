"""
Pydantic Schemas cho Medication History & Smart Reminders (Stage 10).
Đồng bộ 100% Data Contract với Frontend DTOs (frontend/src/types/history_reminder.ts).
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ScanHistoryCreate(BaseModel):
    source_type: str = Field(..., description="Nguồn trích xuất ('prescription' | 'packaging' | 'manual')")
    drug_names: List[str] = Field(..., description="Danh sách tên các thuốc trong phiên scan")
    highest_severity: str = Field("NONE", description="Mức độ cảnh báo cao nhất ('HIGH' | 'MEDIUM' | 'LOW' | 'NONE')")
    summary: Optional[str] = Field(None, description="Tóm tắt kết quả đánh giá")
    raw_payload: Optional[Dict[str, Any]] = Field(None, description="Payload báo cáo chi tiết để khôi phục")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class ScanHistoryResponse(BaseModel):
    id: str = Field(..., description="ID định danh lịch sử phiên scan")
    user_id: str = Field(..., description="ID tài khoản sở hữu")
    scanned_at: str = Field(..., description="Thời gian thực hiện (ISO 8601 string)")
    source_type: str = Field(..., description="Nguồn trích xuất")
    drug_names: List[str] = Field(..., description="Danh sách tên các thuốc")
    highest_severity: str = Field(..., description="Mức độ cảnh báo cao nhất")
    summary: Optional[str] = Field(None, description="Tóm tắt kết quả đánh giá")
    raw_payload: Optional[Dict[str, Any]] = Field(None, description="Payload báo cáo chi tiết")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class ReminderCreate(BaseModel):
    drug_name: str = Field(..., description="Tên thuốc cần nhắc nhở")
    dosage_instruction: Optional[str] = Field(None, description="Hướng dẫn liều dùng (VD: 1 viên sau ăn)")
    time_of_day: str = Field(..., description="Buổi trong ngày ('morning' | 'noon' | 'afternoon' | 'evening')")
    reminder_time: str = Field("08:00", description="Giờ nhắc nhở (HH:MM)")
    is_active: bool = Field(True, description="Trạng thái bật/tắt nhắc nhở")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class ReminderUpdate(BaseModel):
    dosage_instruction: Optional[str] = Field(None, description="Hướng dẫn liều dùng")
    time_of_day: Optional[str] = Field(None, description="Buổi trong ngày")
    reminder_time: Optional[str] = Field(None, description="Giờ nhắc nhở")
    is_active: Optional[bool] = Field(None, description="Trạng thái bật/tắt nhắc nhở")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class ReminderLogCreate(BaseModel):
    status: str = Field(..., description="Trạng thái uống ('taken' | 'skipped')")
    notes: Optional[str] = Field(None, description="Ghi chú thêm")

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
    taken_count: int = Field(0, description="Số lần đã đánh dấu uống thuốc")
    skipped_count: int = Field(0, description="Số lần bỏ qua")
    adherence_rate: float = Field(0.0, description="Tỉ lệ tuân thủ điều trị % (0.0 -> 100.0)")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
