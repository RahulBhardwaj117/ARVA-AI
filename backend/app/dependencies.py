"""Reusable FastAPI dependencies."""

import uuid
from collections.abc import Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.permissions import Permission, role_has_permission
from app.auth.tokens import decode_access_token
from app.database.session import get_db
from app.models.user import User
from app.repositories.users import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


class APIError(Exception):
    """Application exception rendered through the standard error envelope."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_db),
) -> User:
    """Resolve the current active user from a bearer token."""
    token = (
        credentials.credentials
        if credentials is not None
        else request.cookies.get("arva_access_token")
    )
    if token is None:
        raise APIError(
            status_code=401,
            code="AUTHENTICATION_REQUIRED",
            message="A valid bearer token is required.",
        )
    claims = decode_access_token(token)
    if claims is None:
        raise APIError(
            status_code=401,
            code="INVALID_TOKEN",
            message="The access token is invalid or has expired.",
        )
    user = UserRepository(session).get_by_id(uuid.UUID(str(claims.sub)))
    if user is None or not user.is_active:
        raise APIError(
            status_code=401,
            code="INACTIVE_USER",
            message="The user account is inactive or no longer exists.",
        )
    if user.organization_id != claims.organization_id or user.role != claims.role:
        raise APIError(
            status_code=401,
            code="STALE_TOKEN",
            message="The access token no longer matches the user account.",
        )
    return user


def require_permission(permission: Permission) -> Callable[[User], User]:
    """Build a dependency that enforces one role permission."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if not role_has_permission(user.role, permission):
            raise APIError(
                status_code=403,
                code="PERMISSION_DENIED",
                message="Your role does not allow this operation.",
                details={"required_permission": permission.value},
            )
        return user

    return dependency
