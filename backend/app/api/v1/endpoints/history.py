"""
Scan & Evaluation History Endpoints (Stage 10).
API: GET /history/me, POST /history.
Tích hợp AsyncSession kết nối PostgreSQL Database.
"""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.schemas.history_reminder_schema import (
    ScanHistoryCreate,
    ScanHistoryResponse,
)
from app.schemas.user_schema import UserResponse
from app.services.history_service import history_service

router = APIRouter(prefix="/history", tags=["Scan & Evaluation History"])


@router.get(
    "/me",
    response_model=List[ScanHistoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách lịch sử quét & đánh giá thuốc của tôi",
)
async def get_my_history(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ScanHistoryResponse]:
    """Truy xuất dòng thời gian các phiên quét và cảnh báo tương tác đã lưu từ PostgreSQL."""
    return await history_service.get_histories(db, current_user.id)


@router.post(
    "",
    response_model=ScanHistoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Lưu snapshot một phiên quét/đánh giá mới",
)
async def save_scan_history(
    payload: ScanHistoryCreate,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScanHistoryResponse:
    """Lưu lại kết quả trích xuất và phân tích tương tác vào PostgreSQL."""
    return await history_service.save_history(db, current_user.id, payload)
