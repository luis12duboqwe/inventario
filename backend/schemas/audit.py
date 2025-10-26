"""Esquemas relacionados con auditoría para la app de pruebas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AuditStatusResponse(BaseModel):
    """Modelo de respuesta para el endpoint de auditoría del microframework."""

    model_config = ConfigDict(from_attributes=True)

    estatus: str


__all__ = ["AuditStatusResponse"]
