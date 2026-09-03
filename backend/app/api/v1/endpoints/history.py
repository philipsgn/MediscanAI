"""
Scan & Evaluation History Endpoints (Stage 10).
API: GET /history/me, GET /history/{id}, DELETE /history/{id}.
Quy tắc kiến trúc: Không có Public POST /history (History được tạo nội bộ sau khi evaluate thành công).
Tích hợp AsyncSession kết nối PostgreSQL Database.
"""

import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.schemas.history_reminder_schema import (
    PaginatedScanHistoryResponse,
    ScanHistoryResponse,
)
from app.schemas.user_schema import UserResponse
from app.services.history_service import history_service

router = APIRouter(prefix="/history", tags=["Scan & Evaluation History"])


def _get_request_id(request: Request) -> str:
    """Trích xuất hoặc khởi tạo correlation request_id."""
    if request:
        return (
            request.headers.get("X-Request-ID")
            or getattr(getattr(request, "state", None), "request_id", None)
            or str(uuid.uuid4())
        )
    return str(uuid.uuid4())


def _make_history_error_detail(
    error_code: str,
    message: str,
    request_id: str,
    retryable: bool = False,
) -> Dict[str, Any]:
    """Unified 6-Key Error Contract cho phân hệ Lịch sử."""
    return {
        "error_code": error_code,
        "message": message,
        "service": "history",
        "stage": "history_management",
        "request_id": request_id,
        "retryable": retryable,
    }


@router.get(
    "/me",
    response_model=PaginatedScanHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách lịch sử quét & đánh giá thuốc của tôi (Phân trang)",
)
async def get_my_history(
    request: Request,
    response: Response,
    limit: int = Query(50, ge=1, le=100, description="Số bản ghi trên một trang"),
    offset: int = Query(0, ge=0, description="Vị trí bắt đầu"),
    severity: Optional[str] = Query(None, description="Lọc theo mức độ cảnh báo ('HIGH' | 'MEDIUM' | 'LOW' | 'ALL')"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedScanHistoryResponse:
    """Truy xuất dòng thời gian các phiên quét và cảnh báo tương tác đã lưu từ PostgreSQL."""
    request_id = _get_request_id(request)
    response.headers["X-Request-ID"] = request_id
    return await history_service.get_histories(
        db, current_user.id, limit=limit, offset=offset, severity=severity
    )


@router.get(
    "/{history_id}",
    response_model=ScanHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem chi tiết báo cáo phiên quét đã lưu",
)
async def get_history_detail(
    history_id: str,
    request: Request,
    response: Response,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScanHistoryResponse:
    """Truy xuất chi tiết snapshot kết quả đánh giá lâm sàng từ PostgreSQL (Không cần ảnh gốc)."""
    request_id = _get_request_id(request)
    response.headers["X-Request-ID"] = request_id

    record = await history_service.get_history_by_id(db, current_user.id, history_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_history_error_detail(
                error_code="HISTORY_NOT_FOUND",
                message="Không tìm thấy phiên lịch sử quét.",
                request_id=request_id,
            ),
        )
    return record


@router.delete(
    "/{history_id}",
    status_code=status.HTTP_200_OK,
    summary="Xóa một phiên lịch sử quét",
)
async def delete_history(
    history_id: str,
    request: Request,
    response: Response,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Xóa một bản ghi lịch sử khỏi PostgreSQL."""
    request_id = _get_request_id(request)
    response.headers["X-Request-ID"] = request_id

    deleted = await history_service.delete_history(db, current_user.id, history_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_history_error_detail(
                error_code="HISTORY_NOT_FOUND",
                message="Không tìm thấy phiên lịch sử quét cần xóa.",
                request_id=request_id,
            ),
        )
    return {"message": "Xóa lịch sử quét thành công", "id": history_id}
