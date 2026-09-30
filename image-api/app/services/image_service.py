"""Image service — thin façade over the processing pipeline.

CPU-bound Pillow work runs in a thread pool so the FastAPI event loop
is not blocked. The public API stays the same if this later moves to a
process pool or worker queue.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from app.config import Settings, get_settings
from app.models.transforms import TransformSpec
from app.processing.pipeline import run_pipeline

logger = logging.getLogger(__name__)

# Shared pool for CPU-bound image work (v1 — simple and correct)
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="image-worker")


class ImageService:
    """Orchestrates image transformation requests."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def transform(
        self,
        data: bytes,
        spec: TransformSpec,
    ) -> tuple[bytes, str]:
        """
        Transform an uploaded image according to ``spec``.

        Returns ``(encoded_bytes, content_type)``.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            _executor,
            run_pipeline,
            data,
            spec,
            self.settings,
        )


def get_image_service(settings: Settings | None = None) -> ImageService:
    """
    Factory used by FastAPI dependency injection.

    Prefer injecting Settings via ``Depends(get_settings)`` at the route
    and constructing the service with those settings so tests can override.
    """
    return ImageService(settings=settings or get_settings())
