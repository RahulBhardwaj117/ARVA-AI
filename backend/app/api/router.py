"""Versioned API router."""

from fastapi import APIRouter, Depends

from app.api.auth import router as auth_router
from app.api.platform import router as platform_router
from app.auth.permissions import Permission
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.user import UserRead

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(platform_router)


@api_router.get(
    "/operator-check",
    response_model=UserRead,
    tags=["authorization"],
)
def operator_check(
    user: User = Depends(require_permission(Permission.OPERATE_INFRASTRUCTURE)),
) -> UserRead:
    """Demonstrate a foundation-level permission boundary."""
    return UserRead.model_validate(user)
