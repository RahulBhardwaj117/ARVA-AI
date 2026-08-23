"""User response schemas."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.models.user import UserRole

EmailAddress = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=3,
        max_length=320,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    ),
]


class OrganizationSummary(BaseModel):
    """Minimal organization details returned with the current user."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    deployment_mode: str


class UserRead(BaseModel):
    """Safe user representation that excludes password material."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    email: EmailAddress
    role: UserRole
    is_active: bool
    last_login_at: datetime | None
    organization: OrganizationSummary
