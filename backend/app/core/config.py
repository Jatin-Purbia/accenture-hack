"""Centralized application configuration.

All runtime configuration is sourced from environment variables (via .env in
development). Nothing here is hardcoded per-deployment — this module is the
single place that reads the process environment so the rest of the codebase
can depend on typed settings instead of `os.environ` scattered around.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://localhost:5174"

    # LLM provider
    llm_provider: str = "openai"
    openai_api_key: str | None = None
    openai_model_cheap: str = "gpt-4o-mini"
    openai_model_strong: str = "gpt-4o"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model_cheap: str = "qwen2.5:1.5b"
    ollama_model_strong: str = "qwen2.5:3b"

    # Data locations (relative to backend/app/core/, resolved to absolute)
    data_raw_dir: str = "../data/raw"
    data_processed_dir: str = "../data/processed"

    # Confidence / abstention thresholds
    confidence_abstain_margin: float = 0.12
    confidence_low_threshold: float = 0.55
    confidence_high_threshold: float = 0.75

    # Cost tiering: insights with confidence >= cutoff use the cheap model tier
    llm_tier_confidence_cutoff: float = 0.75

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def data_raw_path(self) -> Path:
        return (_BACKEND_DIR / self.data_raw_dir).resolve()

    @property
    def data_processed_path(self) -> Path:
        return (_BACKEND_DIR / self.data_processed_dir).resolve()

    @property
    def repo_root(self) -> Path:
        return _BACKEND_DIR.parent

    @property
    def docs_path(self) -> Path:
        return self.repo_root / "docs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
