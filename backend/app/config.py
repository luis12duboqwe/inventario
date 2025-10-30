"""Configuración general de la aplicación Softmobile Central."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import (
    AliasChoices,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    return normalized not in {"", "0", "false", "no", "off"}


_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Valores de configuración cargados desde variables de entorno."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="allow",
    )

    database_url: str = Field(
        ...,
        validation_alias=AliasChoices("DATABASE_URL", "SOFTMOBILE_DATABASE_URL"),
    )
    title: str = Field(default="Softmobile Central")
    version: str = Field(default="2.2.0")
    secret_key: str = Field(
        ...,
        validation_alias=AliasChoices(
            "JWT_SECRET_KEY",
            "SOFTMOBILE_SECRET_KEY",
            "SECRET_KEY",
        ),
    )
    bootstrap_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "SOFTMOBILE_BOOTSTRAP_TOKEN",
            "BOOTSTRAP_TOKEN",
        ),
    )
    access_token_expire_minutes: int = Field(
        ...,
        validation_alias=AliasChoices(
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            "SOFTMOBILE_TOKEN_MINUTES",
        ),
    )
    session_cookie_expire_minutes: int = Field(
        default=480,
        validation_alias=AliasChoices(
            "SESSION_COOKIE_EXPIRE_MINUTES",
            "SOFTMOBILE_SESSION_COOKIE_MINUTES",
        ),
    )
    max_failed_login_attempts: int = Field(
        default=5,
        validation_alias=AliasChoices(
            "MAX_FAILED_LOGIN_ATTEMPTS",
            "SOFTMOBILE_MAX_FAILED_LOGIN_ATTEMPTS",
        ),
    )
    account_lock_minutes: int = Field(
        default=15,
        validation_alias=AliasChoices(
            "ACCOUNT_LOCK_MINUTES",
            "SOFTMOBILE_ACCOUNT_LOCK_MINUTES",
        ),
    )
    password_reset_token_minutes: int = Field(
        default=30,
        validation_alias=AliasChoices(
            "PASSWORD_RESET_TOKEN_MINUTES",
            "SOFTMOBILE_PASSWORD_RESET_MINUTES",
        ),
    )
    sync_interval_seconds: int = Field(
        default=1800,
        validation_alias=AliasChoices(
            "SYNC_INTERVAL_SECONDS",
            "SOFTMOBILE_SYNC_INTERVAL_SECONDS",
        ),
    )
    sync_retry_interval_seconds: int = Field(
        default=600,
        validation_alias=AliasChoices(
            "SYNC_RETRY_INTERVAL_SECONDS",
            "SOFTMOBILE_SYNC_RETRY_INTERVAL_SECONDS",
        ),
    )
    sync_max_attempts: int = Field(
        default=5,
        validation_alias=AliasChoices(
            "SYNC_MAX_ATTEMPTS",
            "SOFTMOBILE_SYNC_MAX_ATTEMPTS",
        ),
    )
    enable_background_scheduler: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "ENABLE_BACKGROUND_SCHEDULER",
            "SOFTMOBILE_ENABLE_SCHEDULER",
        ),
    )
    enable_backup_scheduler: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "ENABLE_BACKUP_SCHEDULER",
            "SOFTMOBILE_ENABLE_BACKUP_SCHEDULER",
        ),
    )
    enable_catalog_pro: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "ENABLE_CATALOG_PRO",
            "SOFTMOBILE_ENABLE_CATALOG_PRO",
        ),
    )
    enable_transfers: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "ENABLE_TRANSFERS",
            "SOFTMOBILE_ENABLE_TRANSFERS",
        ),
    )
    enable_purchases_sales: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "ENABLE_PURCHASES_SALES",
            "SOFTMOBILE_ENABLE_PURCHASES_SALES",
        ),
    )
    enable_analytics_adv: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "ENABLE_ANALYTICS_ADV",
            "SOFTMOBILE_ENABLE_ANALYTICS_ADV",
        ),
    )
    enable_2fa: bool = Field(
        default=False,
        validation_alias=AliasChoices("ENABLE_2FA", "SOFTMOBILE_ENABLE_2FA"),
    )
    enable_hybrid_prep: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "ENABLE_HYBRID_PREP",
            "SOFTMOBILE_ENABLE_HYBRID_PREP",
        ),
    )
    inventory_low_stock_threshold: int = Field(
        default=5,
        validation_alias=AliasChoices(
            "INVENTORY_LOW_STOCK_THRESHOLD",
            "SOFTMOBILE_LOW_STOCK_THRESHOLD",
        ),
    )
    inventory_adjustment_variance_threshold: int = Field(
        default=3,
        validation_alias=AliasChoices(
            "INVENTORY_ADJUSTMENT_VARIANCE_THRESHOLD",
            "SOFTMOBILE_ADJUSTMENT_VARIANCE_THRESHOLD",
        ),
    )
    cost_method: str = Field(
        default="FIFO",
        validation_alias=AliasChoices("COST_METHOD", "SOFTMOBILE_COST_METHOD"),
    )  # // [PACK30-31-BACKEND]
    backup_interval_seconds: int = Field(
        default=43200,
        validation_alias=AliasChoices(
            "BACKUP_INTERVAL_SECONDS",
            "SOFTMOBILE_BACKUP_INTERVAL_SECONDS",
        ),
    )
    backup_directory: str = Field(
        default="./backups",
        validation_alias=AliasChoices("BACKUP_DIR", "SOFTMOBILE_BACKUP_DIR"),
    )
    update_feed_path: str = Field(
        default="./docs/releases.json",
        validation_alias=AliasChoices(
            "UPDATE_FEED_PATH",
            "SOFTMOBILE_UPDATE_FEED_PATH",
        ),
    )
    session_cookie_name: str = Field(
        default="softmobile_session",
        validation_alias=AliasChoices(
            "SESSION_COOKIE_NAME",
            "SOFTMOBILE_SESSION_COOKIE_NAME",
        ),
    )
    session_cookie_secure: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "SESSION_COOKIE_SECURE",
            "SOFTMOBILE_SESSION_COOKIE_SECURE",
        ),
    )
    session_cookie_samesite: str = Field(
        default="lax",
        validation_alias=AliasChoices(
            "SESSION_COOKIE_SAMESITE",
            "SOFTMOBILE_SESSION_COOKIE_SAMESITE",
        ),
    )
    allowed_origins: list[str] = Field(
        ...,
        validation_alias=AliasChoices("CORS_ORIGINS", "SOFTMOBILE_ALLOWED_ORIGINS"),
    )
    testing_mode: bool = Field(
        default=False,
        validation_alias=AliasChoices("SOFTMOBILE_TEST_MODE", "TESTING_MODE"),
    )

    @model_validator(mode="after")
    def _ensure_testing_flag(self) -> "Settings":
        if bool(os.getenv("PYTEST_CURRENT_TEST")):
            self.testing_mode = True
        return self

    @field_validator(
        "access_token_expire_minutes",
        "sync_interval_seconds",
        "sync_retry_interval_seconds",
        "sync_max_attempts",
        "backup_interval_seconds",
        "session_cookie_expire_minutes",
        "max_failed_login_attempts",
        "account_lock_minutes",
        "password_reset_token_minutes",
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

    @field_validator("session_cookie_samesite", mode="before")
    @classmethod
    def _normalize_samesite(cls, value: Any) -> str:
        if value is None:
            return "lax"
        normalized = str(value).strip().lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("session_cookie_samesite debe ser lax, strict o none")
        return normalized

    @field_validator(
        "inventory_low_stock_threshold",
        "inventory_adjustment_variance_threshold",
    )
    @classmethod
    def _ensure_non_negative(cls, value: int, info: ValidationInfo) -> int:
        if value < 0:
            raise ValueError(f"{info.field_name} debe ser mayor o igual que cero")
        return value

    @field_validator("cost_method", mode="before")
    @classmethod
    def _normalize_cost_method(cls, value: str | None) -> str:
        normalized = (value or "FIFO").strip().upper()
        if normalized not in {"FIFO", "AVG"}:
            return "FIFO"
        return normalized  # // [PACK30-31-BACKEND]

    @field_validator(
        "enable_background_scheduler",
        "enable_backup_scheduler",
        "enable_catalog_pro",
        "enable_transfers",
        "enable_purchases_sales",
        "enable_analytics_adv",
        "enable_2fa",
        "enable_hybrid_prep",
        "session_cookie_secure",
    )
    @classmethod
    def _coerce_bool(cls, value: bool | str | int | None) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if value is None:
            return False
        return _is_truthy(str(value))

    @model_validator(mode="after")
    def _validate_required(self) -> "Settings":
        missing: list[str] = []
        if not self.database_url:
            missing.append("DATABASE_URL")
        if not self.secret_key:
            missing.append("JWT_SECRET_KEY")
        if not self.allowed_origins:
            missing.append("CORS_ORIGINS")
        if missing:
            raise ValueError(
                "Faltan variables de entorno obligatorias: " + ", ".join(missing)
            )
        return self

try:
    settings = Settings()
except ValidationError as exc:  # pragma: no cover - validado en pruebas manuales
    missing = [
        str(error.get("loc", ("",))[0])
        for error in exc.errors()
        if error.get("type") == "missing"
    ]
    details = ", ".join(sorted(set(missing))) or "valores requeridos"
    raise RuntimeError(
        "Faltan variables de entorno obligatorias para iniciar el backend: "
        f"{details}."
    ) from exc
