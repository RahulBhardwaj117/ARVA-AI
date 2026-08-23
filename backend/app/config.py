"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Typed ARVA runtime settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ARVA_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "ARVA AI — Autonomous Decision Intelligence System"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = Field(
        default="development-only-change-this-secret-key",
        min_length=32,
    )
    access_token_expire_minutes: int = Field(default=30, ge=5, le=1440)
    database_url: str = "sqlite:///./arva.db"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    demo_admin_email: str = "admin@arva.local"
    demo_admin_password: str = "ArvaDemo!2026"
    demo_organization: str = "ARVA Labs"
    rate_limit_requests: int = Field(default=240, ge=30, le=10_000)
    rate_limit_window_seconds: int = Field(default=60, ge=10, le=3600)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        """Accept comma-separated origins as well as JSON arrays."""
        if isinstance(value, str) and not value.strip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def production_secret_is_explicit(self) -> "Settings":
        """Reject the documented development signing key in production."""
        if (
            self.environment.lower() == "production"
            and self.secret_key == "development-only-change-this-secret-key"
        ):
            raise ValueError("ARVA_SECRET_KEY must be replaced in production")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
