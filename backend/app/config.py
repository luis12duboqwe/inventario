"""Configuración general de la aplicación Softmobile Central."""
from __future__ import annotations

import os
from pydantic import BaseModel, Field, field_validator
from pydantic import ValidationInfo
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Valores de configuración cargados desde variables de entorno."""

    database_url: str = Field(
        default_factory=lambda: os.getenv("SOFTMOBILE_DATABASE_URL", "sqlite:///./softmobile.db")
    )
    title: str = Field(default="Softmobile Central")
    version: str = Field(default="0.1.0")
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
        default_factory=lambda: os.getenv("SOFTMOBILE_ENABLE_SCHEDULER", "1") not in {"0", "false", "False"}
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

    @field_validator("access_token_expire_minutes", "sync_interval_seconds", "backup_interval_seconds")
    @classmethod
    def _ensure_positive(cls, value: int, info: ValidationInfo) -> int:
        if value <= 0:
            raise ValueError(f"{info.field_name} debe ser mayor que cero")
        return value


settings = Settings()
