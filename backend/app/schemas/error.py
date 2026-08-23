"""Consistent API error envelope."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Machine- and human-readable API error."""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str


class ErrorResponse(BaseModel):
    """Top-level API error response."""

    error: ErrorDetail

