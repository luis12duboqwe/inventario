"""Esquemas Pydantic centralizados para la API de Softmobile Central."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_serializer, field_validator

from ..models import BackupMode, MovementType, SyncMode, SyncStatus


class StoreBase(BaseModel):
    name: str = Field(..., max_length=120, description="Nombre visible de la sucursal")
    location: str | None = Field(default=None, max_length=120, description="Dirección o referencia")
    timezone: str = Field(default="UTC", max_length=50, description="Zona horaria de la sucursal")


class StoreCreate(StoreBase):
    """Carga de datos necesaria para registrar una nueva sucursal."""


class StoreUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    timezone: str | None = Field(default=None, max_length=50)


class StoreResponse(StoreBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class DeviceBase(BaseModel):
    sku: str = Field(..., max_length=80, description="Identificador único del producto")
    name: str = Field(..., max_length=120, description="Descripción del dispositivo")
    quantity: int = Field(default=0, ge=0, description="Cantidad disponible en inventario")
    unit_price: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Precio unitario referencial del dispositivo",
    )

    @field_serializer("unit_price")
    @classmethod
    def _serialize_unit_price(cls, value: Decimal) -> float:
        return float(value)


class DeviceCreate(DeviceBase):
    """Datos necesarios para registrar un dispositivo."""


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    quantity: int | None = Field(default=None, ge=0)
    unit_price: Decimal | None = Field(default=None, ge=Decimal("0"))


class DeviceResponse(DeviceBase):
    id: int
    store_id: int

    model_config = ConfigDict(from_attributes=True)

    @computed_field(return_type=float)  # type: ignore[misc]
    def inventory_value(self) -> float:
        return float(self.quantity * self.unit_price)


class RoleResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    username: str = Field(..., max_length=80)
    full_name: str | None = Field(default=None, max_length=120)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    roles: list[str] = Field(default_factory=list)


class UserRolesUpdate(BaseModel):
    roles: list[str] = Field(default_factory=list)


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    roles: list[RoleResponse]

    model_config = ConfigDict(from_attributes=True)

    @field_validator("roles", mode="before")
    @classmethod
    def _flatten_roles(cls, value: Any) -> list[RoleResponse]:
        if value is None:
            return []
        flattened: list[RoleResponse] = []
        for item in value:
            if isinstance(item, RoleResponse):
                flattened.append(item)
                continue
            role_obj = getattr(item, "role", item)
            flattened.append(RoleResponse.model_validate(role_obj))
        return flattened


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: int


class MovementBase(BaseModel):
    device_id: int = Field(..., ge=1)
    movement_type: MovementType
    quantity: int = Field(..., gt=0)
    reason: str | None = Field(default=None, max_length=255)


class MovementCreate(MovementBase):
    """Carga de datos para registrar movimientos de inventario."""


class MovementResponse(MovementBase):
    id: int
    store_id: int
    performed_by_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventorySummary(BaseModel):
    store_id: int
    store_name: str
    total_items: int
    total_value: Decimal
    devices: list[DeviceResponse]

    @field_serializer("total_value")
    @classmethod
    def _serialize_total_value(cls, value: Decimal) -> float:
        return float(value)


class StoreValueMetric(BaseModel):
    store_id: int
    store_name: str
    device_count: int
    total_units: int
    total_value: Decimal

    @field_serializer("total_value")
    @classmethod
    def _serialize_metric_value(cls, value: Decimal) -> float:
        return float(value)


class LowStockDevice(BaseModel):
    store_id: int
    store_name: str
    device_id: int
    sku: str
    name: str
    quantity: int
    unit_price: Decimal

    @field_serializer("unit_price")
    @classmethod
    def _serialize_low_stock_price(cls, value: Decimal) -> float:
        return float(value)

    @computed_field(return_type=float)  # type: ignore[misc]
    def inventory_value(self) -> float:
        return float(self.quantity * self.unit_price)


class InventoryTotals(BaseModel):
    stores: int
    devices: int
    total_units: int
    total_value: Decimal

    @field_serializer("total_value")
    @classmethod
    def _serialize_totals_value(cls, value: Decimal) -> float:
        return float(value)


class InventoryMetricsResponse(BaseModel):
    totals: InventoryTotals
    top_stores: list[StoreValueMetric]
    low_stock_devices: list[LowStockDevice]


class SyncSessionResponse(BaseModel):
    id: int
    store_id: int | None
    mode: SyncMode
    status: SyncStatus
    started_at: datetime
    finished_at: datetime | None
    triggered_by_id: int | None
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)


class SyncRequest(BaseModel):
    store_id: int | None = Field(default=None, ge=1)


class AuditLogResponse(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: str
    details: str | None
    performed_by_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BackupRunRequest(BaseModel):
    nota: str | None = Field(default=None, max_length=255)


class BackupJobResponse(BaseModel):
    id: int
    mode: BackupMode
    executed_at: datetime
    pdf_path: str
    archive_path: str
    total_size_bytes: int
    notes: str | None
    triggered_by_id: int | None

    model_config = ConfigDict(from_attributes=True)


class ReleaseInfo(BaseModel):
    version: str = Field(..., description="Versión disponible del producto")
    release_date: date = Field(..., description="Fecha oficial de liberación")
    notes: str = Field(..., description="Resumen de cambios relevantes")
    download_url: str = Field(..., description="Enlace de descarga del instalador")


class UpdateStatus(BaseModel):
    current_version: str
    latest_version: str | None
    is_update_available: bool
    latest_release: ReleaseInfo | None = None


__all__ = [
    "AuditLogResponse",
    "BackupJobResponse",
    "BackupRunRequest",
    "DeviceBase",
    "DeviceCreate",
    "DeviceResponse",
    "DeviceUpdate",
    "InventoryMetricsResponse",
    "InventorySummary",
    "InventoryTotals",
    "LowStockDevice",
    "MovementBase",
    "MovementCreate",
    "MovementResponse",
    "ReleaseInfo",
    "RoleResponse",
    "StoreBase",
    "StoreCreate",
    "StoreResponse",
    "StoreUpdate",
    "StoreValueMetric",
    "SyncRequest",
    "SyncSessionResponse",
    "TokenPayload",
    "TokenResponse",
    "UpdateStatus",
    "UserBase",
    "UserCreate",
    "UserResponse",
    "UserRolesUpdate",
]
