"""Crop operation with strict bounds validation."""

from __future__ import annotations

from PIL import Image

from app.errors import AppError
from app.models.transforms import CropOperation


def apply(image: Image.Image, params: CropOperation) -> Image.Image:
    """
    Crop a rectangle from ``image``.

    Raises ``AppError`` if the crop region exceeds image bounds.
    """
    img_w, img_h = image.size
    left = params.x
    top = params.y
    right = params.x + params.width
    bottom = params.y + params.height

    if left < 0 or top < 0:
        raise AppError(
            "INVALID_OPERATION",
            "Crop origin must be non-negative",
        )

    if right > img_w or bottom > img_h:
        raise AppError(
            "INVALID_OPERATION",
            (
                f"Crop region exceeds image bounds "
                f"(image={img_w}x{img_h}, "
                f"crop=({left},{top},{right},{bottom}))"
            ),
        )

    return image.crop((left, top, right, bottom))
