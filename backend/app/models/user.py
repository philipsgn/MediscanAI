"""
SQLAlchemy Model cho bảng `users` (Stage 8/10).
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.profile import UserProfileModel
    from app.models.medication import UserMedicationModel
    from app.models.history import ScanHistoryModel
    from app.models.reminder import ReminderModel


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_profile_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
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
    profile: Mapped[Optional["UserProfileModel"]] = relationship(
        "UserProfileModel",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    medications: Mapped[List["UserMedicationModel"]] = relationship(
        "UserMedicationModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    scan_histories: Mapped[List["ScanHistoryModel"]] = relationship(
        "ScanHistoryModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    reminders: Mapped[List["ReminderModel"]] = relationship(
        "ReminderModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )

