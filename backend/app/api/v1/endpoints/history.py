"""
Scan & Evaluation History Endpoints (Stage 10).
API: GET /history/me, POST /history.
Yêu cầu Bearer Token xác thực.
"""

from typing import List
from fastapi import APIRouter, Depends, status
from app.api.v1.endpoints.auth import get_current_user
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
) -> List[ScanHistoryResponse]:
    """Truy xuất dòng thời gian các phiên quét và cảnh báo tương tác đã lưu."""
    return history_service.get_histories(current_user.id)


@router.post(
    "",
    response_model=ScanHistoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Lưu snapshot một phiên quét/đánh giá mới",
)
async def save_scan_history(
    payload: ScanHistoryCreate,
    current_user: UserResponse = Depends(get_current_user),
) -> ScanHistoryResponse:
    """Lưu lại kết quả trích xuất và phân tích tương tác gắn với tài khoản người dùng."""
    return history_service.save_history(current_user.id, payload)
