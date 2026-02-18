"""
config.py — Environment configuration for the API.

Uses pydantic-settings for type-safe environment variable handling.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

# Load .env file if it exists
def _load_dotenv():
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if key and value and key not in os.environ:
                        os.environ[key] = value

_load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        # API Keys
        self.anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")

        # Server settings
        self.host: str = os.environ.get("HOST", "0.0.0.0")
        self.port: int = int(os.environ.get("PORT", "8000"))
        self.debug: bool = os.environ.get("DEBUG", "false").lower() == "true"

        # CORS settings
        self.cors_origins: list = os.environ.get(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
        ).split(",")

        # File storage
        self.output_dir: str = os.environ.get("OUTPUT_DIR", "./output")
        self.max_file_age_hours: int = int(os.environ.get("MAX_FILE_AGE_HOURS", "24"))

        # LLM settings
        self.default_model: str = os.environ.get("DEFAULT_MODEL", "claude-sonnet-4-20250514")
        self.max_tokens: int = int(os.environ.get("MAX_TOKENS", "4096"))

        # Rate limiting
        self.rate_limit_requests: int = int(os.environ.get("RATE_LIMIT_REQUESTS", "100"))
        self.rate_limit_window_seconds: int = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60"))

    @property
    def has_anthropic_key(self) -> bool:
        """Check if Anthropic API key is configured."""
        return bool(self.anthropic_api_key)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
