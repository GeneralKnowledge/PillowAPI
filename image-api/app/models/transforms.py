"""Pydantic models for transformation specifications."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


class ResizeOperation(BaseModel):
    """Resize an image, optionally preserving aspect ratio."""

    type: Literal["resize"] = "resize"
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    fit: Literal["stretch", "contain", "cover"] = "stretch"

    @model_validator(mode="after")
    def require_at_least_one_dimension(self) -> ResizeOperation:
        if self.width is None and self.height is None:
            raise ValueError("resize requires at least one of width or height")
        return self


class CropOperation(BaseModel):
    """Crop a rectangular region from an image."""

    type: Literal["crop"] = "crop"
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class GrayscaleOperation(BaseModel):
    """Convert an image to grayscale."""

    type: Literal["grayscale"] = "grayscale"


class RotateOperation(BaseModel):
    """Rotate an image by an arbitrary angle in degrees."""

    type: Literal["rotate"] = "rotate"
    degrees: float
    expand: bool = True


class FlipOperation(BaseModel):
    """Flip an image horizontally or vertically."""

    type: Literal["flip"] = "flip"
    direction: Literal["horizontal", "vertical"]


class BlurOperation(BaseModel):
    """Apply a Gaussian blur."""

    type: Literal["blur"] = "blur"
    radius: float = Field(ge=0, le=100)


Operation = Annotated[
    ResizeOperation
    | CropOperation
    | GrayscaleOperation
    | RotateOperation
    | FlipOperation
    | BlurOperation,
    Field(discriminator="type"),
]


class OutputSpec(BaseModel):
    """Output encoding options."""

    format: Literal["jpeg", "png", "webp"] = "jpeg"
    quality: int = Field(default=85, ge=1, le=100)


class TransformSpec(BaseModel):
    """Declarative sequence of image operations and output settings."""

    operations: list[Operation] = Field(default_factory=list)
    output: OutputSpec = Field(default_factory=OutputSpec)
