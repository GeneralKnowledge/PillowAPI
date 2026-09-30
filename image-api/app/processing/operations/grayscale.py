"""Grayscale conversion via Pillow."""

from __future__ import annotations

from PIL import Image, ImageOps

from app.models.transforms import GrayscaleOperation


def apply(image: Image.Image, params: GrayscaleOperation) -> Image.Image:
    """Convert ``image`` to grayscale, preserving alpha when present."""
    del params  # no parameters
    # ImageOps.grayscale returns mode "L"; preserve alpha via convert path
    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        rgba = image.convert("RGBA")
        gray = ImageOps.grayscale(rgba)
        # Re-attach alpha channel
        alpha = rgba.getchannel("A")
        result = gray.convert("LA")
        result.putalpha(alpha)
        return result
    return ImageOps.grayscale(image)
