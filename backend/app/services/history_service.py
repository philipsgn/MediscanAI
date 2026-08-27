"""
History Service — Quản lý Lịch sử Quét & Đánh giá Tương tác Thuốc trong PostgreSQL.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.history import ScanHistoryModel
from app.schemas.history_reminder_schema import (
    ScanHistoryCreate,
    ScanHistoryResponse,
)

logger = logging.getLogger(__name__)


class HistoryService:
    async def save_history(self, db: AsyncSession, user_id: str, data: ScanHistoryCreate) -> ScanHistoryResponse:
        """Lưu lại một phiên quét & đánh giá thuốc gắn liền với user_id vào PostgreSQL."""
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

    async def get_histories(self, db: AsyncSession, user_id: str) -> List[ScanHistoryResponse]:
        """Truy xuất danh sách lịch sử các phiên scan của một user_id từ PostgreSQL."""
        stmt = (
            select(ScanHistoryModel)
            .where(ScanHistoryModel.user_id == user_id)
            .order_by(desc(ScanHistoryModel.scanned_at))
        )
        result = await db.execute(stmt)
        items = result.scalars().all()

        return [
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
        ]


history_service = HistoryService()
