"""Esquemas para el centro de ayuda y modo demostración."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class HelpGuide(BaseModel):
    """Guía contextual asociada a un módulo."""

    module: str = Field(description="Identificador del módulo (inventory, operations, analytics, security, help)")
    title: str = Field(description="Título corto de la guía")
    summary: str = Field(description="Descripción ejecutiva")
    steps: List[str] = Field(default_factory=list, description="Pasos rápidos o checklists")
    manual: str = Field(description="Ruta relativa al manual PDF en docs/capacitacion")
    video: str = Field(description="Ruta relativa al guion de video o clip alojado en docs/capacitacion")


class DemoDataset(BaseModel):
    """Dataset ficticio usado para el modo demostración."""

    inventory: List[dict] = Field(default_factory=list, description="Dispositivos simulados")
    operations: List[dict] = Field(default_factory=list, description="Operaciones de referencia")
    contacts: List[dict] = Field(default_factory=list, description="Clientes/proveedores de ejemplo")


class HelpCenterResponse(BaseModel):
    """Respuesta consolidada para las guías de ayuda."""

    guides: List[HelpGuide]
    manuals_base_path: str = Field(default="docs/capacitacion")
    demo_mode_enabled: bool = Field(default=False)


class DemoPreview(BaseModel):
    """Detalle del estado y datos del modo demo."""

    enabled: bool = Field(description="Flag global de modo demostración")
    notice: str = Field(description="Mensaje de alcance y aislamiento")
    dataset: Optional[DemoDataset] = Field(
        default=None, description="Dataset ficticio solo cuando el modo demo está activo"
    )
