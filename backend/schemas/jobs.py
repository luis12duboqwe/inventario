"""Esquemas para el módulo de trabajos asincrónicos."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExportJobRequest(BaseModel):
    """Parámetros aceptados para solicitar una exportación."""

    format: Literal["csv", "pdf", "xlsx"] = Field(
        ..., description="Formato deseado para la exportación"
    )
    store_id: int | None = Field(
        default=None,
        ge=1,
        description="Identificador opcional de la sucursal a exportar",
    )
    filters: dict[str, str] | None = Field(
        default=None,
        description="Filtros adicionales que serán aplicados al job",
    )

    model_config = ConfigDict(extra="forbid")


class ExportJobResponse(BaseModel):
    """Descripción pública de un job encolado."""

    job_id: str = Field(..., min_length=8, max_length=64)
    status: Literal["queued", "processing"] = Field(...)
    backend: Literal["local", "redis"] = Field(...)
    requested_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(extra="forbid")
