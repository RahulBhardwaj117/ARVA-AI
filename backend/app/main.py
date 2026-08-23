"""FastAPI application entry point."""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

import redis
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import Response

from app.api.health import router as health_router
from app.api.router import api_router
from app.api.websockets import router as websocket_router
from app.config import get_settings
from app.dependencies import APIError
from app.logging import configure_logging

configure_logging()
logger = logging.getLogger("arva.api")
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Predictive, explainable and policy-governed AI infrastructure control plane.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(api_router, prefix=settings.api_v1_prefix)
app.include_router(websocket_router)


def error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    """Build the standard API error envelope."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
                "request_id": getattr(request.state, "request_id", "unknown"),
            }
        },
    )


@app.exception_handler(APIError)
async def handle_api_error(request: Request, exc: APIError) -> JSONResponse:
    """Render application errors without exposing stack traces."""
    return error_response(
        request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Render request validation errors consistently."""
    safe_errors = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    return error_response(
        request,
        status_code=422,
        code="VALIDATION_ERROR",
        message="The request did not pass validation.",
        details={"errors": safe_errors},
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Log unexpected failures and return a safe response."""
    logger.exception(
        "unhandled_request_error",
        extra={"request_id": getattr(request.state, "request_id", "unknown")},
    )
    return error_response(
        request,
        status_code=500,
        code="INTERNAL_ERROR",
        message="An unexpected error occurred.",
    )


@app.middleware("http")
async def request_context(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Attach request IDs and emit structured request logs."""
    request_id = request.headers.get("x-request-id") or f"REQ-{uuid.uuid4().hex[:12].upper()}"
    request.state.request_id = request_id
    started = time.perf_counter()
    client_host = request.client.host if request.client else "unknown"
    request_limit = 20 if request.url.path.endswith("/auth/login") else settings.rate_limit_requests
    try:
        limiter = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=0.08,
            socket_timeout=0.12,
        )
        bucket = int(time.time()) // settings.rate_limit_window_seconds
        rate_key = f"arva:rate:{client_host}:{request.url.path}:{bucket}"
        count = limiter.incr(rate_key)
        if count == 1:
            limiter.expire(rate_key, settings.rate_limit_window_seconds + 5)
        if count > request_limit:
            response = error_response(
                request,
                status_code=429,
                code="RATE_LIMIT_EXCEEDED",
                message="Too many requests. Retry after the current rate window.",
                details={"retry_after_seconds": settings.rate_limit_window_seconds},
            )
            response.headers["retry-after"] = str(settings.rate_limit_window_seconds)
            return response
    except redis.RedisError:
        # Availability is preferable to blocking the API when the limiter is unavailable.
        pass
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    response.headers["x-content-type-options"] = "nosniff"
    response.headers["x-frame-options"] = "DENY"
    response.headers["referrer-policy"] = "strict-origin-when-cross-origin"
    response.headers["permissions-policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path in {"/docs", "/redoc"}:
        response.headers["content-security-policy"] = (
            "default-src 'self' https://cdn.jsdelivr.net; "
            "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
            "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
            "img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'"
        )
    else:
        response.headers["content-security-policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        )
    logger.info(
        "request_completed",
        extra={"request_id": request_id},
        stack_info=False,
    )
    response.headers["server-timing"] = f"app;dur={(time.perf_counter() - started) * 1000:.2f}"
    return response
