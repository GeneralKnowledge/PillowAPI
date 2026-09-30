"""Resize operation with stretch / contain / cover fit modes."""

from __future__ import annotations

from PIL import Image

from app.errors import AppError
from app.models.transforms import ResizeOperation


def apply(image: Image.Image, params: ResizeOperation) -> Image.Image:
    """
    Resize ``image`` according to ``params``.

    When only one of width/height is set, the other is derived from the
    original aspect ratio. Fit modes:

    * ``stretch`` — force exact dimensions (default when both given)
    * ``contain`` — fit inside the box, preserving aspect ratio
    * ``cover`` — fill the box, preserving aspect ratio (may crop)
    """
    src_w, src_h = image.size
    if src_w <= 0 or src_h <= 0:
        raise AppError("INVALID_IMAGE", "Image has invalid dimensions")

    target_w = params.width
    target_h = params.height

    # Single-dimension resize: preserve aspect ratio
    if target_w is None and target_h is not None:
        target_w = max(1, round(src_w * (target_h / src_h)))
        return image.resize((target_w, target_h), Image.Resampling.LANCZOS)

    if target_h is None and target_w is not None:
        target_h = max(1, round(src_h * (target_w / src_w)))
        return image.resize((target_w, target_h), Image.Resampling.LANCZOS)

    assert target_w is not None and target_h is not None

    if params.fit == "stretch":
        return image.resize((target_w, target_h), Image.Resampling.LANCZOS)

    if params.fit == "contain":
        return _fit_contain(image, target_w, target_h)

    if params.fit == "cover":
        return _fit_cover(image, target_w, target_h)

    raise AppError("INVALID_PARAMETER", f"Unknown fit mode: {params.fit!r}")


def _fit_contain(image: Image.Image, box_w: int, box_h: int) -> Image.Image:
    """Scale image to fit entirely within the box, preserving aspect ratio."""
    src_w, src_h = image.size
    scale = min(box_w / src_w, box_h / src_h)
    new_w = max(1, round(src_w * scale))
    new_h = max(1, round(src_h * scale))
    return image.resize((new_w, new_h), Image.Resampling.LANCZOS)


def _fit_cover(image: Image.Image, box_w: int, box_h: int) -> Image.Image:
    """Scale and center-crop so the result fills the box exactly."""
    src_w, src_h = image.size
    scale = max(box_w / src_w, box_h / src_h)
    new_w = max(1, round(src_w * scale))
    new_h = max(1, round(src_h * scale))
    resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    left = max(0, (new_w - box_w) // 2)
    top = max(0, (new_h - box_h) // 2)
    right = left + box_w
    bottom = top + box_h

    # Clamp in case of rounding edge cases
    right = min(right, new_w)
    bottom = min(bottom, new_h)
    cropped = resized.crop((left, top, right, bottom))

    # Ensure exact target size if rounding left a 1px gap
    if cropped.size != (box_w, box_h):
        cropped = cropped.resize((box_w, box_h), Image.Resampling.LANCZOS)
    return cropped
