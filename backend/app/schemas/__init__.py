"""Esquemas Pydantic centralizados para la API de Softmobile Central."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_serializer, field_validator

from datetime import datetime

from ..models import (
    BackupMode,
    CommercialState,
    MovementType,
    SyncMode,
    SyncStatus,
    TransferStatus,
)


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
    imei: str | None = Field(default=None, max_length=18, description="IMEI del dispositivo")
    serial: str | None = Field(default=None, max_length=120, description="Número de serie")
    marca: str | None = Field(default=None, max_length=80, description="Marca comercial")
    modelo: str | None = Field(default=None, max_length=120, description="Modelo detallado")
    color: str | None = Field(default=None, max_length=60, description="Color principal")
    capacidad_gb: int | None = Field(default=None, ge=0, description="Capacidad de almacenamiento en GB")
    estado_comercial: CommercialState = Field(default=CommercialState.NUEVO)
    proveedor: str | None = Field(default=None, max_length=120, description="Proveedor principal")
    costo_unitario: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Costo neto por unidad",
    )
    margen_porcentaje: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Margen aplicado en porcentaje",
    )
    garantia_meses: int = Field(default=0, ge=0, description="Garantía ofrecida en meses")
    lote: str | None = Field(default=None, max_length=80, description="Identificador de lote")
    fecha_compra: date | None = Field(default=None, description="Fecha de compra al proveedor")

    @field_serializer("unit_price")
    @classmethod
    def _serialize_unit_price(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("costo_unitario")
    @classmethod
    def _serialize_cost(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("margen_porcentaje")
    @classmethod
    def _serialize_margin(cls, value: Decimal) -> float:
        return float(value)

    @field_validator("imei")
    @classmethod
    def validate_imei(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if normalized and not (10 <= len(normalized) <= 18):
            raise ValueError("IMEI inválido")
        return normalized or None

    @field_validator("serial")
    @classmethod
    def validate_serial(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if normalized and len(normalized) < 4:
            raise ValueError("Número de serie inválido")
        return normalized or None


class DeviceCreate(DeviceBase):
    """Datos necesarios para registrar un dispositivo."""


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    quantity: int | None = Field(default=None, ge=0)
    unit_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    imei: str | None = Field(default=None, max_length=18)
    serial: str | None = Field(default=None, max_length=120)
    marca: str | None = Field(default=None, max_length=80)
    modelo: str | None = Field(default=None, max_length=120)
    color: str | None = Field(default=None, max_length=60)
    capacidad_gb: int | None = Field(default=None, ge=0)
    estado_comercial: CommercialState | None = Field(default=None)
    proveedor: str | None = Field(default=None, max_length=120)
    costo_unitario: Decimal | None = Field(default=None, ge=Decimal("0"))
    margen_porcentaje: Decimal | None = Field(default=None, ge=Decimal("0"))
    garantia_meses: int | None = Field(default=None, ge=0)
    lote: str | None = Field(default=None, max_length=80)
    fecha_compra: date | None = Field(default=None)

    @field_validator("imei")
    @classmethod
    def validate_update_imei(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if normalized and not (10 <= len(normalized) <= 18):
            raise ValueError("IMEI inválido")
        return normalized or None

    @field_validator("serial")
    @classmethod
    def validate_update_serial(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if normalized and len(normalized) < 4:
            raise ValueError("Número de serie inválido")
        return normalized or None


class DeviceResponse(DeviceBase):
    id: int
    store_id: int

    model_config = ConfigDict(from_attributes=True)

    @computed_field(return_type=float)  # type: ignore[misc]
    def inventory_value(self) -> float:
        return float(self.quantity * self.unit_price)


class DeviceSearchFilters(BaseModel):
    imei: str | None = Field(default=None, max_length=18)
    serial: str | None = Field(default=None, max_length=120)
    capacidad_gb: int | None = Field(default=None, ge=0)
    color: str | None = Field(default=None, max_length=60)
    marca: str | None = Field(default=None, max_length=80)
    modelo: str | None = Field(default=None, max_length=120)

    model_config = ConfigDict(extra="forbid")

    @field_validator("imei", "serial", "color", "marca", "modelo", mode="before")
    @classmethod
    def _normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None


class CatalogProDeviceResponse(DeviceResponse):
    store_name: str

    model_config = ConfigDict(from_attributes=True)


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
    pass


class TransferOrderItemBase(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)


class TransferOrderItemCreate(TransferOrderItemBase):
    pass


class TransferOrderTransition(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


class TransferOrderCreate(BaseModel):
    origin_store_id: int = Field(..., ge=1)
    destination_store_id: int = Field(..., ge=1)
    reason: str | None = Field(default=None, max_length=255)
    items: list[TransferOrderItemCreate]

    @field_validator("reason")
    @classmethod
    def _normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("items")
    @classmethod
    def _ensure_items(cls, value: list[TransferOrderItemCreate]) -> list[TransferOrderItemCreate]:
        if not value:
            raise ValueError("Debes incluir al menos un dispositivo en la transferencia.")
        return value


class TransferOrderItemResponse(TransferOrderItemBase):
    id: int
    transfer_order_id: int

    model_config = ConfigDict(from_attributes=True)


class TransferOrderResponse(BaseModel):
    id: int
    origin_store_id: int
    destination_store_id: int
    status: TransferStatus
    reason: str | None
    created_at: datetime
    updated_at: datetime
    dispatched_at: datetime | None
    received_at: datetime | None
    cancelled_at: datetime | None
    items: list[TransferOrderItemResponse]

    model_config = ConfigDict(from_attributes=True)


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
