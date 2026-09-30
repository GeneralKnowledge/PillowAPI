"""Consistent API error types and helpers."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Application error with a stable machine-readable code."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def error_body(code: str, message: str) -> dict[str, dict[str, str]]:
    """Build the standard error response payload."""
    return {"error": {"code": code, "message": message}}


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """Serialize AppError into the standard JSON error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.code, exc.message),
    )
