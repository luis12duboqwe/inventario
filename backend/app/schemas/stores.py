"""Esquemas para la gestión de sucursales."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class StoreBase(BaseModel):
    name: str = Field(..., max_length=120,
                      description="Nombre visible de la sucursal")
    location: str | None = Field(
        default=None, max_length=255, description="Dirección física o referencia de la sucursal"
    )
    phone: str | None = Field(
        default=None, max_length=30, description="Teléfono de contacto principal"
    )
    manager: str | None = Field(
        default=None, max_length=120, description="Responsable operativo de la sucursal"
    )
    status: str = Field(
        default="activa", max_length=30, description="Estado operativo de la sucursal"
    )
    timezone: str = Field(default="UTC", max_length=50,
                          description="Zona horaria de la sucursal")


class StoreCreate(StoreBase):
    """Carga de datos necesaria para registrar una nueva sucursal."""

    code: str | None = Field(
        default=None,
        max_length=20,
        description="Código interno único de la sucursal",
    )


class StoreUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    manager: str | None = Field(default=None, max_length=120)
    status: str | None = Field(default=None, max_length=30)
    code: str | None = Field(default=None, max_length=20)
    timezone: str | None = Field(default=None, max_length=50)


class StoreResponse(StoreBase):
    id: int
    code: str
    created_at: datetime
    inventory_value: Decimal = Field(default=Decimal("0"))

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("inventory_value")
    @classmethod
    def _serialize_inventory_value(cls, value: Decimal) -> float:
        return float(value)


class StoreMembershipBase(BaseModel):
    user_id: int = Field(..., ge=1)
    store_id: int = Field(..., ge=1)
    can_create_transfer: bool = Field(default=False)
    can_receive_transfer: bool = Field(default=False)


class StoreMembershipResponse(StoreMembershipBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StoreMembershipUpdate(StoreMembershipBase):
    """Actualiza los permisos de pertenencia de un usuario en una sucursal."""
