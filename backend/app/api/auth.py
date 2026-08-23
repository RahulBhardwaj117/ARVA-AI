"""Authentication API routes."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.session import get_db
from app.dependencies import APIError, get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserRead
from app.services.auth import AuthenticationError, AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    response: Response,
    session: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate an active user."""
    try:
        result = AuthService(session).login(payload.email, payload.password)
        response.set_cookie(
            key="arva_access_token",
            value=result.access_token,
            max_age=result.expires_in,
            httponly=True,
            secure=get_settings().environment.lower() == "production",
            samesite="lax",
            path="/",
        )
        return result
    except AuthenticationError as exc:
        raise APIError(
            status_code=401,
            code="INVALID_CREDENTIALS",
            message="The email or password is incorrect.",
        ) from exc


@router.get("/me", response_model=UserRead)
def current_user(user: User = Depends(get_current_user)) -> UserRead:
    """Return the authenticated user and organization."""
    return UserRead.model_validate(user)


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    """Clear the HTTP-only session cookie."""
    response.delete_cookie("arva_access_token", path="/")
