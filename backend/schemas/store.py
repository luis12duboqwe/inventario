"""Esquemas ligeros para exponer información de sucursales."""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from backend.app import schemas as core_schemas
from backend.schemas.common import Page


class StoreBase(BaseModel):
    """Campos comunes para las sucursales del backend ligero."""

    name: str = Field(..., min_length=3, max_length=120)
    code: str | None = Field(default=None, min_length=3, max_length=20)
    address: str | None = Field(default=None, max_length=255)
    is_active: bool = True
    timezone: str | None = Field(default="UTC", max_length=50)

    @field_validator("name")
    @classmethod
    def _normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("El nombre de la sucursal debe tener al menos 3 caracteres.")
        return normalized

    @field_validator("code")
    @classmethod
    def _normalize_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if len(normalized) < 3:
            raise ValueError("El código debe contar con al menos 3 caracteres.")
        return normalized

    @field_validator("address")
    @classmethod
    def _normalize_address(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("timezone")
    @classmethod
    def _normalize_timezone(cls, value: str | None) -> str:
        normalized = (value or "UTC").strip()
        return normalized or "UTC"


class StoreCreate(StoreBase):
    """Carga útil para crear una nueva sucursal."""

    def to_core(self) -> core_schemas.StoreCreate:
        return core_schemas.StoreCreate(
            name=self.name,
            location=self.address,
            phone=None,
            manager=None,
            status="activa" if self.is_active else "inactiva",
            timezone=self.timezone or "UTC",
            code=self.code,
        )


class StoreUpdate(BaseModel):
    """Campos opcionales para actualizar una sucursal existente."""

    name: str | None = Field(default=None, min_length=3, max_length=120)
    code: str | None = Field(default=None, min_length=3, max_length=20)
    address: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    timezone: str | None = Field(default=None, max_length=50)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("El nombre de la sucursal debe tener al menos 3 caracteres.")
        return normalized

    @field_validator("code")
    @classmethod
    def _validate_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if len(normalized) < 3:
            raise ValueError("El código debe contar con al menos 3 caracteres.")
        return normalized

    @field_validator("address")
    @classmethod
    def _validate_address(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def to_core(self) -> core_schemas.StoreUpdate:
        status: str | None
        if self.is_active is None:
            status = None
        else:
            status = "activa" if self.is_active else "inactiva"
        return core_schemas.StoreUpdate(
            name=self.name,
            location=self.address,
            status=status,
            code=self.code,
            timezone=self.timezone,
        )


class StoreRead(StoreBase):
    """Representación pública de una sucursal."""

    id: int
    code: str
    created_at: datetime
    status: str
    inventory_value: float = 0.0

    @classmethod
    def from_core(cls, store: core_schemas.StoreResponse) -> "StoreRead":
        return cls(
            id=store.id,
            name=store.name,
            code=store.code,
            address=store.location,
            is_active=store.status.lower() != "inactiva",
            timezone=store.timezone,
            created_at=store.created_at,
            status=store.status,
            inventory_value=float(store.inventory_value),
        )


class StoreMembershipBase(BaseModel):
    store_id: int = Field(..., ge=1)
    user_id: int = Field(..., ge=1)
    can_create_transfer: bool = False
    can_receive_transfer: bool = False

    def to_core(self) -> core_schemas.StoreMembershipUpdate:
        return core_schemas.StoreMembershipUpdate(
            store_id=self.store_id,
            user_id=self.user_id,
            can_create_transfer=self.can_create_transfer,
            can_receive_transfer=self.can_receive_transfer,
        )


class StoreMembershipUpdate(StoreMembershipBase):
    """Actualización o creación de membresías de sucursal."""


class StoreMembershipRead(StoreMembershipBase):
    """Respuesta pública para las membresías de sucursal."""

    id: int
    created_at: datetime

    @classmethod
    def from_core(cls, membership: core_schemas.StoreMembershipResponse) -> "StoreMembershipRead":
        return cls(
            id=membership.id,
            store_id=membership.store_id,
            user_id=membership.user_id,
            can_create_transfer=membership.can_create_transfer,
            can_receive_transfer=membership.can_receive_transfer,
            created_at=membership.created_at,
        )


__all__ = [
    "Page",
    "StoreBase",
    "StoreCreate",
    "StoreRead",
    "StoreUpdate",
    "StoreMembershipRead",
    "StoreMembershipUpdate",
]
