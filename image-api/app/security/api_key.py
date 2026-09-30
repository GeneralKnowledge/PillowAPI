"""API-key authentication via the X-API-Key header."""

from __future__ import annotations

from fastapi import Depends, Header, Request

from app.config import Settings, get_settings
from app.errors import AppError


def require_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    """
    Enforce API-key authentication when enabled.

    When ``API_KEY_ENABLED`` is false, all requests are allowed.
    Health checks are exempt so load balancers can probe freely.
    """
    # Health is always public
    if request.url.path == "/health":
        return

    if not settings.api_key_enabled:
        return

    if not settings.api_key:
        raise AppError(
            "UNAUTHORIZED",
            "API key authentication is enabled but no API key is configured",
            status_code=401,
        )

    if not x_api_key or x_api_key != settings.api_key:
        raise AppError(
            "UNAUTHORIZED",
            "Missing or invalid API key",
            status_code=401,
        )
