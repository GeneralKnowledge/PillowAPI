"""Pillow Image Manipulation API — FastAPI application entrypoint."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import get_settings
from app.errors import AppError, app_error_handler, error_body

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Pillow Image Manipulation API",
    description=(
        "Accept an image and a declarative sequence of operations, "
        "apply them with Pillow, and return the resulting image."
    ),
    version="0.1.0",
)

app.add_exception_handler(AppError, app_error_handler)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Normalize FastAPI/Pydantic request validation errors."""
    errors = exc.errors()
    if errors:
        first = errors[0]
        loc = " → ".join(str(part) for part in first.get("loc", ()))
        msg = first.get("msg", "validation error")
        message = f"{loc}: {msg}" if loc else msg
    else:
        message = "Request validation failed"
    return JSONResponse(
        status_code=422,
        content=error_body("INVALID_PARAMETER", message),
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """Catch-all: log internals, return a safe client message."""
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content=error_body(
            "PROCESSING_FAILED",
            "An unexpected error occurred while processing the request",
        ),
    )


app.include_router(router)
