"""User persistence model and role definitions."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(StrEnum):
    """Roles supported by the ARVA control plane."""

    ADMINISTRATOR = "administrator"
    INFRASTRUCTURE_OPERATOR = "infrastructure_operator"
    AI_ENGINEER = "ai_engineer"
    RESEARCHER = "researcher"
    VIEWER = "viewer"
    AUDITOR = "auditor"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Authenticated operator scoped to one organization."""

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_organization_email", "organization_id", "email", unique=True),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=32),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    organization: Mapped["Organization"] = relationship(back_populates="users")  # noqa: F821

