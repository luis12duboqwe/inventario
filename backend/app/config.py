"""Configuración general de la aplicación Softmobile Central."""
from __future__ import annotations

import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Valores de configuración cargados desde variables de entorno."""

    database_url: str = Field(
        default_factory=lambda: os.getenv("SOFTMOBILE_DATABASE_URL", "sqlite:///./softmobile.db")
    )
    title: str = Field(default="Softmobile Central")
    version: str = Field(default="0.1.0")


settings = Settings()
