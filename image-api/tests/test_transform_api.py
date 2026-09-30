"""API-level tests for POST /v1/images/transform."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from tests.conftest import make_image, open_bytes

client = TestClient(app)


def _transform(
    image_bytes: bytes | None,
    spec: dict,
    *,
    filename: str = "test.png",
    content_type: str = "image/png",
    headers: dict | None = None,
):
    data = {"spec": json.dumps(spec)}
    files = None
    if image_bytes is not None:
        files = {"file": (filename, image_bytes, content_type)}
    return client.post(
        "/v1/images/transform",
        data=data,
        files=files,
        headers=headers or {},
    )


def test_valid_transform_resize_grayscale() -> None:
    image = make_image(400, 300)
    spec = {
        "operations": [
            {"type": "resize", "width": 200, "height": 150},
            {"type": "grayscale"},
        ],
        "output": {"format": "jpeg", "quality": 85},
    }
    response = _transform(image, spec)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    result = open_bytes(response.content)
    assert result.size == (200, 150)
    assert result.mode == "RGB"  # JPEG is RGB after encoding
    assert result.format == "JPEG"


def test_invalid_image() -> None:
    response = _transform(b"not-an-image", {"operations": [], "output": {"format": "png"}})
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "INVALID_IMAGE"


def test_missing_file() -> None:
    response = client.post(
        "/v1/images/transform",
        data={"spec": json.dumps({"operations": [], "output": {"format": "png"}})},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PARAMETER"


def test_malformed_specification() -> None:
    image = make_image()
    response = client.post(
        "/v1/images/transform",
        data={"spec": "{not-json"},
        files={"file": ("t.png", image, "image/png")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_SPEC"


def test_unsupported_operation() -> None:
    image = make_image()
    spec = {
        "operations": [{"type": "watermark", "text": "x"}],
        "output": {"format": "png"},
    }
    response = _transform(image, spec)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_SPEC"


def test_invalid_parameters_resize_no_dimensions() -> None:
    image = make_image()
    spec = {
        "operations": [{"type": "resize"}],
        "output": {"format": "png"},
    }
    response = _transform(image, spec)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_SPEC"


def test_invalid_crop_exceeds_bounds() -> None:
    image = make_image(100, 100)
    spec = {
        "operations": [
            {"type": "crop", "x": 50, "y": 50, "width": 100, "height": 100}
        ],
        "output": {"format": "png"},
    }
    response = _transform(image, spec)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_OPERATION"
    assert "bounds" in response.json()["error"]["message"].lower()


def test_oversized_upload(monkeypatch: pytest.MonkeyPatch) -> None:
    # Tiny limit so a normal test image trips it
    settings = Settings(max_upload_size=100)
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        image = make_image(200, 200)  # well over 100 bytes as PNG
        assert len(image) > 100
        response = _transform(image, {"operations": [], "output": {"format": "png"}})
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "IMAGE_TOO_LARGE"
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_too_many_operations(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(max_operations=2)
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        image = make_image(50, 50)
        spec = {
            "operations": [
                {"type": "grayscale"},
                {"type": "flip", "direction": "horizontal"},
                {"type": "blur", "radius": 1},
            ],
            "output": {"format": "png"},
        }
        response = _transform(image, spec)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "TOO_MANY_OPERATIONS"
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_png_output_preserves_alpha() -> None:
    image = make_image(40, 40, color=(0, 128, 255, 128), mode="RGBA", fmt="PNG")
    spec = {"operations": [], "output": {"format": "png"}}
    response = _transform(image, spec)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    result = open_bytes(response.content)
    assert result.mode in ("RGBA", "LA", "P")
    # Spot-check that alpha survived
    if result.mode == "RGBA":
        assert result.getpixel((0, 0))[3] == 128


def test_webp_output() -> None:
    image = make_image(60, 40)
    spec = {"operations": [], "output": {"format": "webp", "quality": 80}}
    response = _transform(image, spec)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/webp"
    result = open_bytes(response.content)
    assert result.format == "WEBP"


def test_operation_order_matters() -> None:
    """resize→grayscale vs grayscale→resize should differ after JPEG encode.

    More reliably: crop after resize vs before produces different sizes,
    and we verify the pipeline applies ops in declared order via dimensions.
    """
    image = make_image(200, 200, color=(10, 20, 30))

    spec_a = {
        "operations": [
            {"type": "resize", "width": 100, "height": 100},
            {"type": "crop", "x": 0, "y": 0, "width": 50, "height": 50},
        ],
        "output": {"format": "png"},
    }
    spec_b = {
        "operations": [
            {"type": "crop", "x": 0, "y": 0, "width": 50, "height": 50},
            {"type": "resize", "width": 100, "height": 100},
        ],
        "output": {"format": "png"},
    }

    ra = _transform(image, spec_a)
    rb = _transform(image, spec_b)
    assert ra.status_code == 200 and rb.status_code == 200

    img_a = open_bytes(ra.content)
    img_b = open_bytes(rb.content)
    assert img_a.size == (50, 50)
    assert img_b.size == (100, 100)
    assert img_a.size != img_b.size
