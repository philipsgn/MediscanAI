"""
History Service — Quản lý Lịch sử Quét & Đánh giá Tương tác Thuốc trong PostgreSQL.
Hỗ trợ Internal Write tự động, Phân trang và Bảo mật IDOR.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.history import ScanHistoryModel
from app.schemas.history_reminder_schema import (
    PaginatedScanHistoryResponse,
    ScanHistoryCreate,
    ScanHistoryResponse,
)

logger = logging.getLogger(__name__)


class HistoryService:
    async def create_internal_history(
        self,
        db: AsyncSession,
        user_id: str,
        data: ScanHistoryCreate,
    ) -> ScanHistoryResponse:
        """Ghi nội bộ lịch sử đánh giá thuốc sau khi evaluate thành công (Atomic Internal Write)."""
        history_id = f"hist_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        record = ScanHistoryModel(
            id=history_id,
            user_id=user_id,
            source_type=data.source_type,
            drug_names=data.drug_names,
            highest_severity=data.highest_severity,
            summary=data.summary,
            raw_payload=data.raw_payload,
            scanned_at=now,
        )

        db.add(record)
        await db.commit()
        await db.refresh(record)

        return ScanHistoryResponse(
            id=record.id,
            user_id=record.user_id,
            scanned_at=record.scanned_at.isoformat(),
            source_type=record.source_type,
            drug_names=record.drug_names or [],
            highest_severity=record.highest_severity,
            summary=record.summary,
            raw_payload=record.raw_payload,
        )

    # Alias để giữ tương thích nội bộ
    save_history = create_internal_history

    async def get_histories(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        severity: Optional[str] = None,
    ) -> PaginatedScanHistoryResponse:
        """Truy xuất danh sách lịch sử phân trang của user."""
        base_query = select(ScanHistoryModel).where(ScanHistoryModel.user_id == user_id)
        if severity and severity.upper() != "ALL":
            base_query = base_query.where(ScanHistoryModel.highest_severity == severity.upper())

        # Tổng số bản ghi
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one() or 0

        # Lấy dữ liệu phân trang
        stmt = base_query.order_by(desc(ScanHistoryModel.scanned_at)).limit(limit).offset(offset)
        result = await db.execute(stmt)
        items = result.scalars().all()

        has_more = (offset + len(items)) < total

        return PaginatedScanHistoryResponse(
            items=[
                ScanHistoryResponse(
                    id=item.id,
                    user_id=item.user_id,
                    scanned_at=item.scanned_at.isoformat() if hasattr(item.scanned_at, "isoformat") else str(item.scanned_at),
                    source_type=item.source_type,
                    drug_names=item.drug_names or [],
                    highest_severity=item.highest_severity,
                    summary=item.summary,
                    raw_payload=item.raw_payload,
                )
                for item in items
            ],
            total=total,
            limit=limit,
            offset=offset,
            has_more=has_more,
        )

    async def get_history_by_id(
        self,
        db: AsyncSession,
        user_id: str,
        history_id: str,
    ) -> Optional[ScanHistoryResponse]:
        """Truy xuất chi tiết một bản ghi lịch sử và đối soát quyền sở hữu."""
        stmt = select(ScanHistoryModel).where(
            ScanHistoryModel.id == history_id,
            ScanHistoryModel.user_id == user_id,
        )
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return None

        return ScanHistoryResponse(
            id=record.id,
            user_id=record.user_id,
            scanned_at=record.scanned_at.isoformat() if hasattr(record.scanned_at, "isoformat") else str(record.scanned_at),
            source_type=record.source_type,
            drug_names=record.drug_names or [],
            highest_severity=record.highest_severity,
            summary=record.summary,
            raw_payload=record.raw_payload,
        )

    async def delete_history(
        self,
        db: AsyncSession,
        user_id: str,
        history_id: str,
    ) -> bool:
        """Xóa một bản ghi lịch sử của user."""
        stmt = select(ScanHistoryModel).where(
            ScanHistoryModel.id == history_id,
            ScanHistoryModel.user_id == user_id,
        )
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return False

        await db.delete(record)
        await db.commit()
        return True


history_service = HistoryService()
