"""
User Medications (Cabinet) Endpoints (Stage 10).
API: GET/POST /medications, PUT/DELETE /medications/{id}.
Tích hợp AsyncSession kết nối PostgreSQL Database.
"""

import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.schemas.history_reminder_schema import (
    PaginatedMedicationsResponse,
    UserMedicationCreate,
    UserMedicationResponse,
    UserMedicationUpdate,
)
from app.schemas.user_schema import UserResponse
from app.services.medication_service import medication_service

router = APIRouter(prefix="/medications", tags=["Cabinet & User Medications"])


def _get_request_id(request: Request) -> str:
    """Trích xuất hoặc khởi tạo correlation request_id."""
    if request:
        return (
            request.headers.get("X-Request-ID")
            or getattr(getattr(request, "state", None), "request_id", None)
            or str(uuid.uuid4())
        )
    return str(uuid.uuid4())


def _make_medication_error_detail(
    error_code: str,
    message: str,
    request_id: str,
    retryable: bool = False,
) -> Dict[str, Any]:
    """Unified 6-Key Error Contract cho phân hệ Medications/Cabinet."""
    return {
        "error_code": error_code,
        "message": message,
        "service": "cabinet",
        "stage": "medication_management",
        "request_id": request_id,
        "retryable": retryable,
    }


@router.get(
    "/me",
    response_model=PaginatedMedicationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách thuốc trong Tủ thuốc của tôi",
)
async def get_my_medications(
    request: Request,
    response: Response,
    limit: int = Query(50, ge=1, le=100, description="Số lượng bản ghi trên một trang"),
    offset: int = Query(0, ge=0, description="Vị trí bắt đầu"),
    active_only: bool = Query(False, description="Chỉ lấy thuốc đang sử dụng"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedMedicationsResponse:
    """Truy xuất danh sách thuốc trong Tủ thuốc cá nhân từ PostgreSQL."""
    request_id = _get_request_id(request)
    response.headers["X-Request-ID"] = request_id
    return await medication_service.get_medications(
        db, current_user.id, limit=limit, offset=offset, active_only=active_only
    )


@router.get(
    "/{medication_id}",
    response_model=UserMedicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem chi tiết một thuốc trong Tủ thuốc",
)
async def get_medication_detail(
    medication_id: str,
    request: Request,
    response: Response,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserMedicationResponse:
    """Truy xuất chi tiết một thuốc và đối soát quyền sở hữu."""
    request_id = _get_request_id(request)
    response.headers["X-Request-ID"] = request_id

    med = await medication_service.get_medication_by_id(db, current_user.id, medication_id)
    if not med:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_medication_error_detail(
                error_code="MEDICATION_NOT_FOUND",
                message="Không tìm thấy thuốc trong Tủ thuốc của bạn.",
                request_id=request_id,
            ),
        )
    return med


@router.post(
    "",
    response_model=UserMedicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm thuốc mới vào Tủ thuốc",
)
async def create_medication(
    payload: UserMedicationCreate,
    request: Request,
    response: Response,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserMedicationResponse:
    """Thêm thuốc vào Tủ thuốc trong PostgreSQL gắn liền với user_id."""
    request_id = _get_request_id(request)
    response.headers["X-Request-ID"] = request_id
    return await medication_service.create_medication(db, current_user.id, payload)


@router.put(
    "/{medication_id}",
    response_model=UserMedicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật thông tin thuốc trong Tủ thuốc",
)
async def update_medication(
    medication_id: str,
    payload: UserMedicationUpdate,
    request: Request,
    response: Response,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserMedicationResponse:
    """Cập nhật thông tin liều dùng, ghi chú hoặc trạng thái thuốc."""
    request_id = _get_request_id(request)
    response.headers["X-Request-ID"] = request_id

    updated = await medication_service.update_medication(db, current_user.id, medication_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_medication_error_detail(
                error_code="MEDICATION_NOT_FOUND",
                message="Không tìm thấy thuốc cần cập nhật.",
                request_id=request_id,
            ),
        )
    return updated


@router.delete(
    "/{medication_id}",
    status_code=status.HTTP_200_OK,
    summary="Xóa thuốc khỏi Tủ thuốc",
)
async def delete_medication(
    medication_id: str,
    request: Request,
    response: Response,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Xóa thuốc và tự động dọn dẹp các nhắc nhở liên quan trong PostgreSQL."""
    request_id = _get_request_id(request)
    response.headers["X-Request-ID"] = request_id

    deleted = await medication_service.delete_medication(db, current_user.id, medication_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_medication_error_detail(
                error_code="MEDICATION_NOT_FOUND",
                message="Không tìm thấy thuốc cần xóa.",
                request_id=request_id,
            ),
        )
    return {"message": "Xóa thuốc khỏi Tủ thuốc thành công", "id": medication_id}
