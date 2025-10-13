"""Configuración general de la aplicación Softmobile Central."""
from __future__ import annotations

import os
from pydantic import BaseModel, Field, validator


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

    @validator("access_token_expire_minutes", "sync_interval_seconds")
    def _ensure_positive(cls, value: int, field: Field):  # type: ignore[override]
        if value <= 0:
            raise ValueError(f"{field.name} debe ser mayor que cero")
        return value


settings = Settings()
