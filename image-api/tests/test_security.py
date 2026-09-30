"""API key authentication tests."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from tests.conftest import make_image

client = TestClient(app)


def _override_settings(settings: Settings):
    get_settings.cache_clear()
    app.dependency_overrides[get_settings] = lambda: settings


def _clear_overrides() -> None:
    app.dependency_overrides.pop(get_settings, None)
    get_settings.cache_clear()


def test_health_always_public_with_auth() -> None:
    _override_settings(Settings(api_key_enabled=True, api_key="secret-test-key"))
    try:
        response = client.get("/health")
        assert response.status_code == 200
    finally:
        _clear_overrides()


def test_transform_rejects_missing_key() -> None:
    _override_settings(Settings(api_key_enabled=True, api_key="secret-test-key"))
    try:
        image = make_image(20, 20)
        response = client.post(
            "/v1/images/transform",
            data={"spec": json.dumps({"operations": [], "output": {"format": "png"}})},
            files={"file": ("t.png", image, "image/png")},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "UNAUTHORIZED"
    finally:
        _clear_overrides()


def test_transform_rejects_wrong_key() -> None:
    _override_settings(Settings(api_key_enabled=True, api_key="secret-test-key"))
    try:
        image = make_image(20, 20)
        response = client.post(
            "/v1/images/transform",
            data={"spec": json.dumps({"operations": [], "output": {"format": "png"}})},
            files={"file": ("t.png", image, "image/png")},
            headers={"X-API-Key": "wrong"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "UNAUTHORIZED"
    finally:
        _clear_overrides()


def test_transform_accepts_valid_key() -> None:
    _override_settings(Settings(api_key_enabled=True, api_key="secret-test-key"))
    try:
        image = make_image(20, 20)
        response = client.post(
            "/v1/images/transform",
            data={"spec": json.dumps({"operations": [], "output": {"format": "png"}})},
            files={"file": ("t.png", image, "image/png")},
            headers={"X-API-Key": "secret-test-key"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
    finally:
        _clear_overrides()


def test_auth_disabled_allows_requests() -> None:
    image = make_image(20, 20)
    response = client.post(
        "/v1/images/transform",
        data={"spec": json.dumps({"operations": [], "output": {"format": "png"}})},
        files={"file": ("t.png", image, "image/png")},
    )
    assert response.status_code == 200
