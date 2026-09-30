"""Output format encoding (JPEG, PNG, WebP)."""

from __future__ import annotations

from io import BytesIO

from PIL import Image

from app.errors import AppError
from app.models.transforms import OutputSpec

CONTENT_TYPES: dict[str, str] = {
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}

# Sensible opaque background when flattening transparency for JPEG
_JPEG_BG = (255, 255, 255)


def encode_image(image: Image.Image, output: OutputSpec) -> tuple[bytes, str]:
    """
    Encode ``image`` to the requested format.

    Returns ``(payload_bytes, content_type)``.
    """
    fmt = output.format.lower()
    if fmt not in CONTENT_TYPES:
        raise AppError(
            "UNSUPPORTED_FORMAT",
            f"Unsupported output format: {output.format!r}",
        )

    prepared = _prepare_for_format(image, fmt)
    buffer = BytesIO()
    save_kwargs = _save_kwargs(fmt, output.quality)
    prepared.save(buffer, **save_kwargs)
    return buffer.getvalue(), CONTENT_TYPES[fmt]


def _prepare_for_format(image: Image.Image, fmt: str) -> Image.Image:
    """Convert image mode as needed for the target format."""
    if fmt == "jpeg":
        return _flatten_for_jpeg(image)
    if fmt == "png":
        return _prepare_png(image)
    if fmt == "webp":
        return image
    raise AppError("UNSUPPORTED_FORMAT", f"Unsupported output format: {fmt!r}")


def _flatten_for_jpeg(image: Image.Image) -> Image.Image:
    """
    Convert to RGB suitable for JPEG.

    Transparency is composited onto a white background so alpha is not
    silently discarded.
    """
    if image.mode == "RGB":
        return image

    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, _JPEG_BG)
        background.paste(rgba, mask=rgba.split()[-1])
        return background

    if image.mode == "CMYK":
        return image.convert("RGB")

    return image.convert("RGB")


def _prepare_png(image: Image.Image) -> Image.Image:
    """Preserve alpha when present; otherwise leave mode intact."""
    if image.mode in ("RGBA", "LA", "P", "L", "RGB"):
        return image
    if image.mode == "CMYK":
        return image.convert("RGB")
    return image.convert("RGBA")


def _save_kwargs(fmt: str, quality: int) -> dict:
    """Build Pillow ``save()`` keyword arguments for the format."""
    if fmt == "jpeg":
        return {
            "format": "JPEG",
            "quality": quality,
            "optimize": True,
        }
    if fmt == "png":
        return {
            "format": "PNG",
            "optimize": True,
        }
    if fmt == "webp":
        return {
            "format": "WEBP",
            "quality": quality,
            "method": 4,
        }
    raise AppError("UNSUPPORTED_FORMAT", f"Unsupported output format: {fmt!r}")
