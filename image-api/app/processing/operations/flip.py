"""Horizontal / vertical flip operation."""

from __future__ import annotations

from PIL import Image, ImageOps

from app.errors import AppError
from app.models.transforms import FlipOperation


def apply(image: Image.Image, params: FlipOperation) -> Image.Image:
    """Flip ``image`` horizontally or vertically."""
    if params.direction == "horizontal":
        return ImageOps.mirror(image)
    if params.direction == "vertical":
        return ImageOps.flip(image)
    raise AppError(
        "INVALID_PARAMETER",
        f"Unknown flip direction: {params.direction!r}",
    )
