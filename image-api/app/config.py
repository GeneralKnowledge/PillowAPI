"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the image API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Limits (defaults: ~20 MB, 50 megapixels, 20 operations)
    max_upload_size: int = 20_971_520
    max_image_pixels: int = 50_000_000
    max_operations: int = 20

    # Authentication
    api_key_enabled: bool = False
    api_key: str = ""

    # Logging
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
