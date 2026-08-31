"""
data_capture.py

SQLAlchemy Model cho bảng `scan_records` — Data-Centric AI Platform.
Lưu trữ toàn diện scan lineage, artifacts, automated quality flags,
human corrections (HITL), optimistic locking version, và dataset candidate status.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class ScanRecordModel(Base):
    __tablename__ = "scan_records"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    request_id: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="prescription",
    )
    # Phân định rạch ròi giữa SHA256 (fingerprint) và Storage Ref (URI file thật)
    image_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="",
        index=True,
    )
    image_storage_ref: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
        index=True,
    )
    image_ref: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PROCESSED",
        index=True,
    )
    quality_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )
    quality_flags: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    raw_ocr_result: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    normalized_result: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    clinical_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    corrected_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    is_dataset_candidate: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    dataset_version: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    dataset_tag: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    version_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    # Optimistic locking version để phòng chống Lost Update khi concurrent review
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    reviewed_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    review_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[user_id],
        backref="scan_records",
    )
    reviewer: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[reviewed_by],
    )
