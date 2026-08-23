"""Authentication business logic."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.auth.passwords import verify_password
from app.auth.tokens import create_access_token
from app.repositories.users import UserRepository
from app.schemas.auth import TokenResponse
from app.schemas.user import UserRead


class AuthenticationError(Exception):
    """Raised when credentials cannot authenticate an active user."""


class AuthService:
    """Authenticate users and issue short-lived access tokens."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)

    def login(self, email: str, password: str) -> TokenResponse:
        """Authenticate a user and update the last-login timestamp."""
        user = self.users.get_by_email(email)
        if user is None or not user.is_active or not verify_password(password, user.password_hash):
            raise AuthenticationError

        user.last_login_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(user)
        token, expires_in = create_access_token(
            user_id=user.id,
            organization_id=user.organization_id,
            role=user.role,
        )
        return TokenResponse(
            access_token=token,
            expires_in=expires_in,
            user=UserRead.model_validate(user),
        )

