"""Gaussian blur operation."""

from __future__ import annotations

from PIL import Image, ImageFilter

from app.errors import AppError
from app.models.transforms import BlurOperation


def apply(image: Image.Image, params: BlurOperation) -> Image.Image:
    """Apply a Gaussian blur with the given radius."""
    if params.radius < 0:
        raise AppError("INVALID_PARAMETER", "Blur radius must be >= 0")
    if params.radius == 0:
        return image
    return image.filter(ImageFilter.GaussianBlur(radius=params.radius))
