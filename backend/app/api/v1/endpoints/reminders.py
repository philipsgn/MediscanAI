"""
Smart Dosage Reminders Endpoints (Stage 10).
API: GET/POST /reminders, PUT/DELETE /reminders/{id}, POST /reminders/{id}/log.
Tích hợp AsyncSession kết nối PostgreSQL Database.
"""

import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.schemas.history_reminder_schema import (
    PaginatedRemindersOverviewResponse,
    ReminderCreate,
    ReminderLogCreate,
    ReminderResponse,
    ReminderUpdate,
)
from app.schemas.user_schema import UserResponse
from app.services.reminder_service import reminder_service

router = APIRouter(prefix="/reminders", tags=["Smart Dosage Reminders"])


def _get_request_id(request: Request) -> str:
    """Trích xuất hoặc khởi tạo correlation request_id."""
    if request:
        return (
            request.headers.get("X-Request-ID")
            or getattr(getattr(request, "state", None), "request_id", None)
            or str(uuid.uuid4())
        )
    return str(uuid.uuid4())


def _make_reminder_error_detail(
    error_code: str,
    message: str,
    request_id: str,
    retryable: bool = False,
) -> Dict[str, Any]:
    """Unified 6-Key Error Contract cho phân hệ Nhắc nhở."""
    return {
        "error_code": error_code,
        "message": message,
        "service": "reminders",
        "stage": "reminder_management",
        "request_id": request_id,
        "retryable": retryable,
    }


@router.get(
    "/me",
    response_model=PaginatedRemindersOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách nhắc nhở & tỉ lệ tuân thủ điều trị (Phân trang)",
)
async def get_my_reminders(
    request: Request,
    response: Response,
    limit: int = Query(50, ge=1, le=100, description="Số bản ghi trên một trang"),
    offset: int = Query(0, ge=0, description="Vị trí bắt đầu"),
    active_only: bool = Query(False, description="Chỉ lấy nhắc nhở đang bật"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedRemindersOverviewResponse:
    """Truy xuất danh sách lịch nhắc uống thuốc và chỉ số tuân thủ từ PostgreSQL."""
    request_id = _get_request_id(request)
    response.headers["X-Request-ID"] = request_id
    return await reminder_service.get_reminders(
        db, current_user.id, limit=limit, offset=offset, active_only=active_only
    )


@router.post(
    "",
    response_model=ReminderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo lịch nhắc nhở uống thuốc mới",
)
async def create_reminder(
    payload: ReminderCreate,
    request: Request,
    response: Response,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderResponse:
    """Tạo lịch nhắc uống thuốc theo khung giờ lưu vào PostgreSQL."""
    request_id = _get_request_id(request)
    response.headers["X-Request-ID"] = request_id
    try:
        return await reminder_service.create_reminder(db, current_user.id, payload)
    except ValueError as err:
        if str(err) == "MEDICATION_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_make_reminder_error_detail(
                    error_code="MEDICATION_NOT_FOUND",
                    message="Thuốc liên kết không tồn tại hoặc không thuộc quyền sở hữu của bạn.",
                    request_id=request_id,
                ),
            ) from err
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_make_reminder_error_detail(
                error_code="INVALID_REMINDER_PAYLOAD",
                message=str(err),
                request_id=request_id,
            ),
        ) from err


@router.put(
    "/{reminder_id}",
    response_model=ReminderResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật lịch nhắc nhở",
)
async def update_reminder(
    reminder_id: str,
    payload: ReminderUpdate,
    request: Request,
    response: Response,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderResponse:
    """Sửa đổi thông tin liều dùng, giờ nhắc hoặc bật/tắt nhắc nhở trong PostgreSQL."""
    request_id = _get_request_id(request)
    response.headers["X-Request-ID"] = request_id
    try:
        updated = await reminder_service.update_reminder(db, current_user.id, reminder_id, payload)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_make_reminder_error_detail(
                    error_code="REMINDER_NOT_FOUND",
                    message="Không tìm thấy lịch nhắc nhở cần cập nhật.",
                    request_id=request_id,
                ),
            )
        return updated
    except ValueError as err:
        if str(err) == "MEDICATION_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_make_reminder_error_detail(
                    error_code="MEDICATION_NOT_FOUND",
                    message="Thuốc liên kết không tồn tại hoặc không thuộc quyền sở hữu của bạn.",
                    request_id=request_id,
                ),
            ) from err
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_make_reminder_error_detail(
                error_code="INVALID_REMINDER_PAYLOAD",
                message=str(err),
                request_id=request_id,
            ),
        ) from err


@router.delete(
    "/{reminder_id}",
    status_code=status.HTTP_200_OK,
    summary="Xóa lịch nhắc nhở",
)
async def delete_reminder(
    reminder_id: str,
    request: Request,
    response: Response,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Xóa một nhắc nhở uống thuốc khỏi PostgreSQL."""
    request_id = _get_request_id(request)
    response.headers["X-Request-ID"] = request_id

    deleted = await reminder_service.delete_reminder(db, current_user.id, reminder_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_reminder_error_detail(
                error_code="REMINDER_NOT_FOUND",
                message="Không tìm thấy nhắc nhở để xóa.",
                request_id=request_id,
            ),
        )
    return {"message": "Xóa nhắc nhở thành công", "id": reminder_id}


@router.post(
    "/{reminder_id}/log",
    response_model=ReminderResponse,
    status_code=status.HTTP_200_OK,
    summary="Ghi nhận nhật ký uống thuốc",
)
async def log_reminder_status(
    reminder_id: str,
    payload: ReminderLogCreate,
    request: Request,
    response: Response,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderResponse:
    """Đánh dấu trạng thái 'taken' (Đã uống) hoặc 'skipped' (Bỏ qua)."""
    request_id = _get_request_id(request)
    response.headers["X-Request-ID"] = request_id

    logged = await reminder_service.log_reminder(db, current_user.id, reminder_id, payload)
    if not logged:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_reminder_error_detail(
                error_code="REMINDER_NOT_FOUND",
                message="Không tìm thấy nhắc nhở để ghi nhật ký.",
                request_id=request_id,
            ),
        )
    return logged
