from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RAILCHECK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    backend: str = "fake"
    laya_model: str = "convaiinnovations/laya"
    laya_device: str | None = None
    jev_api_key: str = ""
    jev_base_url: str = "https://api.typesafe.ai"
    jev_model: str = "jev-latest"
    allow_threshold: float = 0.85
    block_threshold: float = 0.85
    noul_positive_threshold: float = 0.5
    harm_block_score: float = 2.0
    host: str = "0.0.0.0"
    port: int = 8080
    max_batch_size: int = 50
    api_key: str = ""
