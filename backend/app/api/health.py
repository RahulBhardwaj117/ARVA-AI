"""Liveness and readiness endpoints."""

from typing import Literal

import redis
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.session import get_db
from app.dependencies import APIError

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health status response."""

    status: Literal["healthy", "ready"]
    service: str
    version: str
    checks: dict[str, str] | None = None


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return process liveness without checking dependencies."""
    return HealthResponse(status="healthy", service="arva-api", version="0.1.0")


@router.get("/ready", response_model=HealthResponse)
def ready(session: Session = Depends(get_db)) -> HealthResponse:
    """Verify that required database and Redis dependencies are available."""
    checks: dict[str, str] = {}
    try:
        session.execute(text("SELECT 1"))
        checks["database"] = "ready"
        client = redis.Redis.from_url(
            get_settings().redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        client.ping()
        checks["redis"] = "ready"
    except Exception as exc:
        # SQLAlchemy raises backend-specific exceptions, rendered without internals.
        raise APIError(
            status_code=503,
            code="DEPENDENCY_UNAVAILABLE",
            message="A required platform dependency is unavailable.",
            details={"checks": checks},
        ) from exc
    return HealthResponse(
        status="ready",
        service="arva-api",
        version="0.1.0",
        checks=checks,
    )
