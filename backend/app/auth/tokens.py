"""JWT creation and validation."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pydantic import BaseModel, ValidationError

from app.config import get_settings
from app.models.user import UserRole

ALGORITHM = "HS256"


class TokenClaims(BaseModel):
    """Claims trusted by authenticated API dependencies."""

    sub: uuid.UUID
    organization_id: uuid.UUID
    role: UserRole
    exp: datetime
    iat: datetime


def create_access_token(
    *,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    role: UserRole,
    expires_delta: timedelta | None = None,
) -> tuple[str, int]:
    """Create a signed short-lived access token and return its lifetime."""
    settings = get_settings()
    lifetime = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "organization_id": str(organization_id),
        "role": role.value,
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM), int(
        lifetime.total_seconds()
    )


def decode_access_token(token: str) -> TokenClaims | None:
    """Decode a signed token, returning ``None`` for invalid claims."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return TokenClaims.model_validate(payload)
    except (jwt.PyJWTError, ValidationError, ValueError):
        return None

