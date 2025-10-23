"""Configuración centralizada para el backend ligero de Softmobile."""
from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Carga los parámetros sensibles y de correo desde ``.env``."""

    SECRET_KEY: str = Field(
        "cambia-este-valor",
        description="Clave usada para firmar y verificar los tokens JWT.",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        60,
        ge=1,
        description="Minutos de vigencia para cada token de acceso.",
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        7,
        ge=1,
        description="Días de vigencia para cada token de refresco.",
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
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="allow",
    )


settings = Settings()

__all__ = ["Settings", "settings"]
