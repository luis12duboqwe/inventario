"""Esquemas Pydantic para validar solicitudes y respuestas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StoreBase(BaseModel):
    name: str = Field(..., max_length=120, description="Nombre visible de la sucursal")
    location: Optional[str] = Field(default=None, max_length=120, description="Dirección o referencia")
    timezone: str = Field(default="UTC", max_length=50, description="Zona horaria de la sucursal")


class StoreCreate(StoreBase):
    pass


class StoreResponse(StoreBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class DeviceBase(BaseModel):
    sku: str = Field(..., max_length=80, description="Identificador único del producto")
    name: str = Field(..., max_length=120, description="Descripción del dispositivo")
    quantity: int = Field(default=0, ge=0, description="Cantidad disponible en inventario")


class DeviceCreate(DeviceBase):
    pass


class DeviceResponse(DeviceBase):
    id: int
    store_id: int

    model_config = ConfigDict(from_attributes=True)
