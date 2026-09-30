"""Rotate operation supporting arbitrary angles."""

from __future__ import annotations

from PIL import Image

from app.models.transforms import RotateOperation


def apply(image: Image.Image, params: RotateOperation) -> Image.Image:
    """
    Rotate ``image`` by ``params.degrees`` counter-clockwise.

    When ``expand`` is true (default), the canvas grows to fit the
    rotated result. Uses a transparent fill for images with alpha,
    otherwise white.
    """
    fillcolor: tuple[int, ...] | int
    if image.mode in ("RGBA", "LA"):
        fillcolor = (0, 0, 0, 0) if image.mode == "RGBA" else (0, 0)
    elif image.mode == "P":
        # Convert palette images so fillcolor is unambiguous
        image = image.convert("RGBA")
        fillcolor = (0, 0, 0, 0)
    elif image.mode == "L":
        fillcolor = 255
    else:
        fillcolor = (255, 255, 255)

    return image.rotate(
        params.degrees,
        resample=Image.Resampling.BICUBIC,
        expand=params.expand,
        fillcolor=fillcolor,
    )
