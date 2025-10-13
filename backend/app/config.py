"""Configuración general de la aplicación Softmobile Central."""
from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class Settings(BaseModel):
    """Valores de configuración cargados desde variables de entorno."""

    database_url: str = Field(
        default_factory=lambda: os.getenv("SOFTMOBILE_DATABASE_URL", "sqlite:///./softmobile.db")
    )
    title: str = Field(default="Softmobile Central")
    version: str = Field(default="2.2.0")
    secret_key: str = Field(
        default_factory=lambda: os.getenv(
            "SOFTMOBILE_SECRET_KEY",
            "softmobile-super-secreto-cambia-esto",
        )
    )
    access_token_expire_minutes: int = Field(
        default_factory=lambda: int(os.getenv("SOFTMOBILE_TOKEN_MINUTES", "60"))
    )
    sync_interval_seconds: int = Field(
        default_factory=lambda: int(os.getenv("SOFTMOBILE_SYNC_INTERVAL_SECONDS", "1800"))
    )
    enable_background_scheduler: bool = Field(
        default_factory=lambda: os.getenv("SOFTMOBILE_ENABLE_SCHEDULER", "1")
        not in {"0", "false", "False"}
    )
    enable_backup_scheduler: bool = Field(
        default_factory=lambda: os.getenv("SOFTMOBILE_ENABLE_BACKUP_SCHEDULER", "1")
        not in {"0", "false", "False"}
    )
    backup_interval_seconds: int = Field(
        default_factory=lambda: int(os.getenv("SOFTMOBILE_BACKUP_INTERVAL_SECONDS", "43200"))
    )
    backup_directory: str = Field(
        default_factory=lambda: os.getenv("SOFTMOBILE_BACKUP_DIR", "./backups")
    )
    update_feed_path: str = Field(
        default_factory=lambda: os.getenv("SOFTMOBILE_UPDATE_FEED_PATH", "./docs/releases.json")
    )
    allowed_origins: list[str] = Field(
        default_factory=lambda: os.getenv("SOFTMOBILE_ALLOWED_ORIGINS", "http://127.0.0.1:5173")
    )

    @field_validator("access_token_expire_minutes", "sync_interval_seconds", "backup_interval_seconds")
    @classmethod
    def _ensure_positive(cls, value: int, info: ValidationInfo) -> int:
        if value <= 0:
            raise ValueError(f"{info.field_name} debe ser mayor que cero")
        return value

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, (list, tuple)):
            return [str(origin).strip() for origin in value if str(origin).strip()]
        raise ValueError("allowed_origins debe ser una lista de orígenes válidos")


settings = Settings()
