"""Shared test helpers — generate images in-memory, no binary fixtures."""

from __future__ import annotations

from io import BytesIO

from PIL import Image


def make_image(
    width: int = 200,
    height: int = 100,
    *,
    color: tuple[int, int, int] | tuple[int, int, int, int] = (255, 0, 0),
    mode: str = "RGB",
    fmt: str = "PNG",
) -> bytes:
    """Create a solid-color test image and return encoded bytes."""
    if mode == "RGBA" and len(color) == 3:
        color = (*color, 255)  # type: ignore[assignment]
    img = Image.new(mode, (width, height), color)
    buf = BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def make_gradient(width: int = 100, height: int = 50) -> Image.Image:
    """Create an RGB gradient useful for order-of-operations tests."""
    img = Image.new("RGB", (width, height))
    pixels = img.load()
    assert pixels is not None
    for x in range(width):
        for y in range(height):
            pixels[x, y] = (x % 256, y % 256, (x + y) % 256)
    return img


def open_bytes(data: bytes) -> Image.Image:
    """Decode image bytes into a Pillow Image (fully loaded)."""
    img = Image.open(BytesIO(data))
    img.load()
    return img
