"""Image processing pipeline: load → validate → transform → encode."""

from __future__ import annotations

import logging
from io import BytesIO

from PIL import Image, ImageFile, ImageOps, UnidentifiedImageError

from app.config import Settings
from app.errors import AppError
from app.models.transforms import TransformSpec
from app.processing.operations import encode_image, get_operation

logger = logging.getLogger(__name__)

# Allow truncated images to raise rather than produce partial results silently
ImageFile.LOAD_TRUNCATED_IMAGES = False


def run_pipeline(
    data: bytes,
    spec: TransformSpec,
    settings: Settings,
) -> tuple[bytes, str]:
    """
    Load an image, apply operations in order, and encode the result.

    Returns ``(encoded_bytes, content_type)``.
    """
    _validate_spec(spec, settings)

    image = _load_image(data, settings)
    image = _normalize_exif(image)

    for operation in spec.operations:
        apply_fn = get_operation(operation.type)
        try:
            image = apply_fn(image, operation)
        except AppError:
            raise
        except Exception as exc:
            logger.exception("Operation %s failed", operation.type)
            raise AppError(
                "PROCESSING_FAILED",
                f"Failed to apply operation {operation.type!r}: {exc}",
                status_code=500,
            ) from exc

    try:
        return encode_image(image, spec.output)
    except AppError:
        raise
    except Exception as exc:
        logger.exception("Failed to encode output image")
        raise AppError(
            "PROCESSING_FAILED",
            f"Failed to encode output image: {exc}",
            status_code=500,
        ) from exc


def _validate_spec(spec: TransformSpec, settings: Settings) -> None:
    if len(spec.operations) > settings.max_operations:
        raise AppError(
            "TOO_MANY_OPERATIONS",
            (
                f"Too many operations: {len(spec.operations)} "
                f"(max {settings.max_operations})"
            ),
        )


def _load_image(data: bytes, settings: Settings) -> Image.Image:
    if not data:
        raise AppError("INVALID_IMAGE", "Uploaded file is empty")

    # Decompression-bomb protection
    Image.MAX_IMAGE_PIXELS = settings.max_image_pixels

    try:
        with Image.open(BytesIO(data)) as img:
            img.load()  # force decode now so errors surface here
            image = img.copy()
    except Image.DecompressionBombError as exc:
        raise AppError(
            "IMAGE_TOO_MANY_PIXELS",
            (
                f"Image exceeds maximum allowed pixels "
                f"({settings.max_image_pixels})"
            ),
        ) from exc
    except UnidentifiedImageError as exc:
        raise AppError(
            "INVALID_IMAGE",
            "Uploaded file is not a valid image",
        ) from exc
    except OSError as exc:
        raise AppError(
            "INVALID_IMAGE",
            f"Failed to decode image: {exc}",
        ) from exc

    width, height = image.size
    pixels = width * height
    if pixels > settings.max_image_pixels:
        raise AppError(
            "IMAGE_TOO_MANY_PIXELS",
            (
                f"Image has {pixels} pixels which exceeds the limit of "
                f"{settings.max_image_pixels}"
            ),
        )

    return image


def _normalize_exif(image: Image.Image) -> Image.Image:
    """Apply EXIF orientation so subsequent ops use upright pixels."""
    try:
        transposed = ImageOps.exif_transpose(image)
    except Exception:
        logger.warning("EXIF transpose failed; continuing with original image")
        return image
    return transposed if transposed is not None else image
