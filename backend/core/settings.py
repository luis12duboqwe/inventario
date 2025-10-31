"""Configuración centralizada para el backend ligero de Softmobile."""
from __future__ import annotations

from pathlib import Path

from pydantic import AliasChoices, Field, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Carga los parámetros sensibles y de correo desde ``.env``."""

    SECRET_KEY: str = Field(
        ...,
        validation_alias=AliasChoices(
            "JWT_SECRET_KEY",
            "SOFTMOBILE_SECRET_KEY",
            "SECRET_KEY",
        ),
        description="Clave usada para firmar y verificar los tokens JWT.",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        ...,
        ge=1,
        validation_alias=AliasChoices(
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            "SOFTMOBILE_TOKEN_MINUTES",
        ),
        description="Minutos de vigencia para cada token de acceso.",
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        7,
        ge=1,
        description="Días de vigencia para cada token de refresco.",
    )
    BOOTSTRAP_TOKEN: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "SOFTMOBILE_BOOTSTRAP_TOKEN",
            "BOOTSTRAP_TOKEN",
        ),
        description=(
            "Token maestro opcional que habilita el bootstrap inicial cuando aún no"
            " existen usuarios registrados."
        ),
    )
    SMTP_HOST: str | None = Field(
        default=None,
        description="Servidor SMTP utilizado para notificaciones por correo.",
    )
    SMTP_PORT: int | None = Field(
        default=None,
        description="Puerto del servidor SMTP.",
    )
    SMTP_USER: str | None = Field(
        default=None,
        description="Usuario para autenticarse en el servidor SMTP.",
    )
    SMTP_PASS: str | None = Field(
        default=None,
        description="Contraseña del usuario SMTP configurado.",
    )
    SMTP_FROM: str | None = Field(
        default=None,
        description="Correo electrónico remitente por defecto para notificaciones.",
    )

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        extra="allow",
    )


    @model_validator(mode="after")
    def _ensure_required(self) -> "Settings":
        missing: list[str] = []
        if not self.SECRET_KEY:
            missing.append("JWT_SECRET_KEY")
        if self.ACCESS_TOKEN_EXPIRE_MINUTES is None:
            missing.append("ACCESS_TOKEN_EXPIRE_MINUTES")
        if missing:
            raise ValueError(
                "Faltan variables de entorno obligatorias: " + ", ".join(missing)
            )
        return self

try:
    settings = Settings()
except ValidationError as exc:  # pragma: no cover - comprobación manual
    missing = [
        str(error.get("loc", ("",))[0])
        for error in exc.errors()
        if error.get("type") == "missing"
    ]
    details = ", ".join(sorted(set(missing))) or "valores requeridos"
    raise RuntimeError(
        "Faltan variables de entorno sensibles para iniciar el backend: "
        f"{details}."
    ) from exc

__all__ = ["Settings", "settings"]
