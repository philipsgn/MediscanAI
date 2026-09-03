"""
SQLAlchemy Model cho bảng `user_medications` (Stage 10).
Quản lý Tủ thuốc (Cabinet) cá nhân hóa của User trên Database PostgreSQL.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.reminder import ReminderModel


class UserMedicationModel(Base):
    __tablename__ = "user_medications"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    brand_name: Mapped[str] = mapped_column(String(255), nullable=False)
    active_ingredient: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    strength: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    dosage_instruction: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    duration_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    user: Mapped["User"] = relationship("User", back_populates="medications")
    reminders: Mapped[List["ReminderModel"]] = relationship(
        "ReminderModel",
        back_populates="medication",
        cascade="all, delete-orphan",
    )
