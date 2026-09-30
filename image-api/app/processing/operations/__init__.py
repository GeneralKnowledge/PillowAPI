"""Operation registry — map operation type names to apply functions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PIL import Image

from app.errors import AppError
from app.processing.operations import blur, crop, flip, format as format_ops
from app.processing.operations import grayscale, resize, rotate

# Signature shared by all operation modules.
ApplyFn = Callable[[Image.Image, Any], Image.Image]

OPERATIONS: dict[str, ApplyFn] = {
    "resize": resize.apply,
    "crop": crop.apply,
    "grayscale": grayscale.apply,
    "rotate": rotate.apply,
    "flip": flip.apply,
    "blur": blur.apply,
}


def get_operation(name: str) -> ApplyFn:
    """Look up an operation by type name."""
    try:
        return OPERATIONS[name]
    except KeyError as exc:
        raise AppError(
            "INVALID_OPERATION",
            f"Unsupported operation type: {name!r}",
        ) from exc


# Re-export format helpers used by the pipeline
encode_image = format_ops.encode_image
CONTENT_TYPES = format_ops.CONTENT_TYPES

__all__ = [
    "OPERATIONS",
    "ApplyFn",
    "CONTENT_TYPES",
    "encode_image",
    "get_operation",
]
