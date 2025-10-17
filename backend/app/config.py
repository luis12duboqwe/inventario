"""Configuración general de la aplicación Softmobile Central."""
from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field, ValidationInfo, field_validator


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    return normalized not in {"", "0", "false", "no", "off"}


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
    sync_retry_interval_seconds: int = Field(
        default_factory=lambda: int(os.getenv("SOFTMOBILE_SYNC_RETRY_INTERVAL_SECONDS", "600"))
    )
    sync_max_attempts: int = Field(
        default_factory=lambda: int(os.getenv("SOFTMOBILE_SYNC_MAX_ATTEMPTS", "5"))
    )
    enable_background_scheduler: bool = Field(
        default_factory=lambda: os.getenv("SOFTMOBILE_ENABLE_SCHEDULER", "1")
        not in {"0", "false", "False"}
    )
    enable_backup_scheduler: bool = Field(
        default_factory=lambda: os.getenv("SOFTMOBILE_ENABLE_BACKUP_SCHEDULER", "1")
        not in {"0", "false", "False"}
    )
    enable_catalog_pro: bool = Field(
        default_factory=lambda: os.getenv("SOFTMOBILE_ENABLE_CATALOG_PRO", "0")
        not in {"0", "false", "False"}
    )
    enable_transfers: bool = Field(
        default_factory=lambda: os.getenv("SOFTMOBILE_ENABLE_TRANSFERS", "0")
        not in {"0", "false", "False"}
    )
    enable_purchases_sales: bool = Field(
        default_factory=lambda: os.getenv("SOFTMOBILE_ENABLE_PURCHASES_SALES", "0")
        not in {"0", "false", "False"}
    )
    enable_analytics_adv: bool = Field(
        default_factory=lambda: os.getenv("SOFTMOBILE_ENABLE_ANALYTICS_ADV", "0")
        not in {"0", "false", "False"}
    )
    enable_2fa: bool = Field(
        default_factory=lambda: os.getenv("SOFTMOBILE_ENABLE_2FA", "0")
        not in {"0", "false", "False"}
    )
    enable_hybrid_prep: bool = Field(
        default_factory=lambda: os.getenv("SOFTMOBILE_ENABLE_HYBRID_PREP", "0")
        not in {"0", "false", "False"}
    )
    inventory_low_stock_threshold: int = Field(
        default_factory=lambda: int(os.getenv("SOFTMOBILE_LOW_STOCK_THRESHOLD", "5"))
    )
    inventory_adjustment_variance_threshold: int = Field(
        default_factory=lambda: int(
            os.getenv("SOFTMOBILE_ADJUSTMENT_VARIANCE_THRESHOLD", "3")
        )
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
    testing_mode: bool = Field(
        default_factory=lambda: _is_truthy(os.getenv("SOFTMOBILE_TEST_MODE"))
        or bool(os.getenv("PYTEST_CURRENT_TEST"))
    )

    @field_validator(
        "access_token_expire_minutes",
        "sync_interval_seconds",
        "sync_retry_interval_seconds",
        "sync_max_attempts",
        "backup_interval_seconds",
    )
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

    @field_validator(
        "inventory_low_stock_threshold",
        "inventory_adjustment_variance_threshold",
    )
    @classmethod
    def _ensure_non_negative(cls, value: int, info: ValidationInfo) -> int:
        if value < 0:
            raise ValueError(f"{info.field_name} debe ser mayor o igual que cero")
        return value


settings = Settings()
