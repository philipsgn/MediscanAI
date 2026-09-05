"""
SQLAlchemy Model cho bảng `learned_drugs` (Stage 18).
Lưu trữ tri thức thuốc tự học với độ bền vững cao, chống ngộ độc cache (Anti-Poisoning),
và ghi nhận số lượt tái sử dụng (Hit Count) để đo lường ROI/Telemetry.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class LearnedDrugModel(Base):
    __tablename__ = "learned_drugs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    brand_name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand_name_normalized: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    active_ingredient: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    strength: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_supplement: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.75, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING_REVIEW",
        nullable=False,
        index=True,
    )  # "PENDING_REVIEW" | "VERIFIED" | "USER_CORRECTED"
    hit_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    verified_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contraindications: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    source: Mapped[str] = mapped_column(String(100), default="ai_llm_inference", nullable=False)

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
