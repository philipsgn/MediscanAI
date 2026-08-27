"""
Smart Dosage Reminders Endpoints (Stage 10).
API: GET /reminders/me, POST /reminders, PUT /reminders/{id}, DELETE /reminders/{id}, POST /reminders/{id}/log.
Tích hợp AsyncSession kết nối PostgreSQL Database.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.schemas.history_reminder_schema import (
    AdherenceStats,
    ReminderCreate,
    ReminderLogCreate,
    ReminderResponse,
    ReminderUpdate,
)
from app.schemas.user_schema import UserResponse
from app.services.reminder_service import reminder_service

router = APIRouter(prefix="/reminders", tags=["Smart Dosage Reminders"])


class RemindersOverviewResponse(BaseModel):
    reminders: List[ReminderResponse]
    stats: AdherenceStats

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


@router.get(
    "/me",
    response_model=RemindersOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách nhắc nhở & tỉ lệ tuân thủ điều trị",
)
async def get_my_reminders(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RemindersOverviewResponse:
    """Truy xuất danh sách lịch nhắc uống thuốc và chỉ số tuân thủ từ PostgreSQL."""
    reminders = await reminder_service.get_reminders(db, current_user.id)
    stats = await reminder_service.get_adherence_stats(db, current_user.id)
    return RemindersOverviewResponse(reminders=reminders, stats=stats)


@router.post(
    "",
    response_model=ReminderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo lịch nhắc nhở uống thuốc mới",
)
async def create_reminder(
    payload: ReminderCreate,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderResponse:
    """Tạo lịch nhắc uống thuốc theo khung giờ lưu vào PostgreSQL."""
    return await reminder_service.create_reminder(db, current_user.id, payload)


@router.put(
    "/{reminder_id}",
    response_model=ReminderResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật lịch nhắc nhở",
)
async def update_reminder(
    reminder_id: str,
    payload: ReminderUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderResponse:
    """Sửa đổi thông tin liều dùng, giờ nhắc hoặc bật/tắt nhắc nhở trong PostgreSQL."""
    try:
        return await reminder_service.update_reminder(db, current_user.id, reminder_id, payload)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@router.delete(
    "/{reminder_id}",
    status_code=status.HTTP_200_OK,
    summary="Xóa lịch nhắc nhở",
)
async def delete_reminder(
    reminder_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Xóa một nhắc nhở uống thuốc khỏi PostgreSQL."""
    deleted = await reminder_service.delete_reminder(db, current_user.id, reminder_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy nhắc nhở để xóa.",
        )
    return {"message": "Xóa nhắc nhở thành công", "id": reminder_id}


@router.post(
    "/{reminder_id}/log",
    response_model=ReminderResponse,
    status_code=status.HTTP_200_OK,
    summary="Ghi nhận trạng thái uống thuốc ('taken' | 'skipped')",
)
async def log_reminder_status(
    reminder_id: str,
    payload: ReminderLogCreate,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderResponse:
    """Đánh dấu 'Đã uống' (taken) hoặc 'Bỏ qua' (skipped) trong PostgreSQL."""
    try:
        return await reminder_service.log_reminder(db, current_user.id, reminder_id, payload)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
