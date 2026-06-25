"""Environment variable wrapper.

Centralizes all configuration so the rest of the app never reads ``os.environ``
directly. Values are loaded from the process environment and an optional
``.env`` file (see ``.env.example``).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, validated and typed at startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App metadata -----------------------------------------------------
    app_name: str = "TinyGuide AI"
    api_version: str = "v1"
    debug: bool = True

    # --- Server -----------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 8000

    # --- CORS -------------------------------------------------------------
    # The Next.js dev server. Comma-separated list in the env var.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- Supabase ---------------------------------------------------------
    supabase_url: str | None = None
    supabase_key: str | None = None

    # --- AI orchestrator (Groq — free, no credit card) --------------------
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"

    # --- AI orchestrator (Claude — optional, paid) ------------------------
    anthropic_api_key: str | None = None
    # Default to the latest, most capable Claude model for the parenting
    # assistant. Override via ANTHROPIC_MODEL if you want a cheaper tier.
    anthropic_model: str = "claude-opus-4-8"

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins as a clean list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton of the settings.

    Using an ``lru_cache`` means the ``.env`` file is parsed exactly once per
    process, and the same object is shared everywhere it is injected.
    """
    return Settings()


settings = get_settings()
