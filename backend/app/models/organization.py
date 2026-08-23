"""Organization persistence model."""

from enum import StrEnum

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DeploymentMode(StrEnum):
    """Supported ARVA operating modes."""

    SIMULATION = "simulation"
    RECOMMENDATION = "recommendation"
    APPROVAL = "approval"
    CONTROLLED_AUTONOMOUS = "controlled_autonomous"


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tenant boundary for users and future infrastructure resources."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    deployment_mode: Mapped[DeploymentMode] = mapped_column(
        Enum(DeploymentMode, native_enum=False, length=32),
        default=DeploymentMode.SIMULATION,
        nullable=False,
    )
    active_policy_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)

    users: Mapped[list["User"]] = relationship(  # noqa: F821
        back_populates="organization",
        cascade="all, delete-orphan",
    )

