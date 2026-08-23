"""Authentication request and response schemas."""

from pydantic import BaseModel, Field

from app.schemas.user import EmailAddress, UserRead


class LoginRequest(BaseModel):
    """Credentials accepted by the login endpoint."""

    email: EmailAddress
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    """Successful authentication response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead
