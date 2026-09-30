"""HTTP routes for the image API."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.errors import AppError
from app.models.transforms import TransformSpec
from app.security.api_key import require_api_key
from app.services.image_service import get_image_service

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@router.post(
    "/v1/images/transform",
    responses={
        200: {
            "content": {
                "image/jpeg": {},
                "image/png": {},
                "image/webp": {},
            },
            "description": "Processed image",
        }
    },
)
async def transform_image(
    file: UploadFile = File(..., description="Source image file"),
    spec: str = Form(
        ...,
        description="JSON transformation specification",
    ),
    _: None = Depends(require_api_key),
    settings: Settings = Depends(get_settings),
) -> Response:
    """
    Apply a declarative sequence of image operations and return the result.
    """
    transform_spec = _parse_spec(spec)
    data = await _read_upload(file, settings)
    service = get_image_service(settings)

    payload, content_type = await service.transform(data, transform_spec)

    return Response(
        content=payload,
        media_type=content_type,
        headers={
            # Filename is never trusted from the upload; use a generic name
            "Content-Disposition": f'inline; filename="result.{transform_spec.output.format}"',
        },
    )


def _parse_spec(raw: str) -> TransformSpec:
    """Parse and validate the JSON transformation specification."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AppError(
            "INVALID_SPEC",
            f"Transformation specification is not valid JSON: {exc.msg}",
        ) from exc

    try:
        return TransformSpec.model_validate(payload)
    except ValidationError as exc:
        # Surface the first validation error clearly
        errors = exc.errors()
        if errors:
            first = errors[0]
            loc = " → ".join(str(part) for part in first.get("loc", ()))
            msg = first.get("msg", "validation error")
            detail = f"{loc}: {msg}" if loc else msg
        else:
            detail = "Invalid transformation specification"
        raise AppError("INVALID_SPEC", detail) from exc


async def _read_upload(file: UploadFile, settings: Settings) -> bytes:
    """Read the uploaded file with a hard size limit."""
    # Prefer declared size when available, but always enforce while reading
    max_size = settings.max_upload_size
    chunks: list[bytes] = []
    total = 0

    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            raise AppError(
                "IMAGE_TOO_LARGE",
                f"Upload exceeds maximum size of {max_size} bytes",
            )
        chunks.append(chunk)

    if total == 0:
        raise AppError("INVALID_IMAGE", "Uploaded file is empty")

    return b"".join(chunks)
