"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Infographix"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # API
    api_prefix: str = "/api/v1"
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Security
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # File storage
    upload_dir: str = "uploads"
    output_dir: str = "outputs"
    max_upload_size_mb: int = 50

    # LLM (external API for prompt parsing only)
    llm_provider: Literal["anthropic", "openai"] = "anthropic"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Database (future)
    database_url: str = "sqlite:///./infographix.db"
    redis_url: str = "redis://localhost:6379/0"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
