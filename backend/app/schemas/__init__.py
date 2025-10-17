"""Esquemas Pydantic centralizados para la API de Softmobile Central."""
from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_serializer,
    field_validator,
    model_validator,
)

from ..models import (
    BackupMode,
    CashSessionStatus,
    CommercialState,
    RecurringOrderType,
    MovementType,
    PaymentMethod,
    PurchaseStatus,
    RepairStatus,
    SyncMode,
    SyncOutboxPriority,
    SyncOutboxStatus,
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
    inventory_value: Decimal = Field(default=Decimal("0"))

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("inventory_value")
    @classmethod
    def _serialize_inventory_value(cls, value: Decimal) -> float:
        return float(value)


class DeviceBase(BaseModel):
    sku: str = Field(..., max_length=80, description="Identificador único del producto")
    name: str = Field(..., max_length=120, description="Descripción del dispositivo")
    quantity: int = Field(default=0, ge=0, description="Cantidad disponible en inventario")
    unit_price: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Precio unitario referencial del dispositivo",
    )
    precio_venta: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Precio público sugerido del dispositivo",
    )
    imei: str | None = Field(default=None, max_length=18, description="IMEI del dispositivo")
    serial: str | None = Field(default=None, max_length=120, description="Número de serie")
    marca: str | None = Field(default=None, max_length=80, description="Marca comercial")
    modelo: str | None = Field(default=None, max_length=120, description="Modelo detallado")
    categoria: str | None = Field(default=None, max_length=80, description="Categoría de catálogo")
    condicion: str | None = Field(default=None, max_length=60, description="Condición física")
    color: str | None = Field(default=None, max_length=60, description="Color principal")
    capacidad_gb: int | None = Field(default=None, ge=0, description="Capacidad de almacenamiento en GB")
    capacidad: str | None = Field(default=None, max_length=80, description="Capacidad descriptiva")
    estado_comercial: CommercialState = Field(default=CommercialState.NUEVO)
    estado: str = Field(
        default="disponible",
        max_length=40,
        description="Estado logístico del producto (disponible, apartado, agotado, etc.)",
    )
    proveedor: str | None = Field(default=None, max_length=120, description="Proveedor principal")
    costo_unitario: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Costo neto por unidad",
    )
    costo_compra: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Costo de compra registrado para el catálogo",
    )
    margen_porcentaje: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Margen aplicado en porcentaje",
    )
    garantia_meses: int = Field(default=0, ge=0, description="Garantía ofrecida en meses")
    lote: str | None = Field(default=None, max_length=80, description="Identificador de lote")
    fecha_compra: date | None = Field(default=None, description="Fecha de compra al proveedor")
    fecha_ingreso: date | None = Field(default=None, description="Fecha de ingreso al inventario")
    ubicacion: str | None = Field(default=None, max_length=120, description="Ubicación física en la sucursal")
    descripcion: str | None = Field(
        default=None,
        max_length=1024,
        description="Descripción extendida o notas del producto",
    )
    imagen_url: str | None = Field(
        default=None,
        max_length=255,
        description="URL de la imagen representativa del producto",
    )

    @field_serializer("unit_price")
    @classmethod
    def _serialize_unit_price(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("precio_venta")
    @classmethod
    def _serialize_sale_price(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("costo_unitario")
    @classmethod
    def _serialize_cost(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("costo_compra")
    @classmethod
    def _serialize_purchase_cost(cls, value: Decimal) -> float:
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

    @model_validator(mode="before")
    @classmethod
    def _map_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "precio_venta" in data and "unit_price" not in data:
                data["unit_price"] = data["precio_venta"]
            if "costo_compra" in data and "costo_unitario" not in data:
                data["costo_unitario"] = data["costo_compra"]
        return data

    @model_validator(mode="after")
    def _sync_aliases(self) -> "DeviceBase":
        object.__setattr__(self, "precio_venta", self.unit_price)
        object.__setattr__(self, "costo_compra", self.costo_unitario)
        return self

    @field_validator(
        "marca",
        "modelo",
        "color",
        "categoria",
        "condicion",
        "capacidad",
        "estado",
        "proveedor",
        "lote",
        "ubicacion",
        "descripcion",
        "imagen_url",
        mode="before",
    )
    @classmethod
    def _normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("estado")
    @classmethod
    def _default_estado(cls, value: str | None) -> str:
        if not value:
            return "disponible"
        return value


class DeviceCreate(DeviceBase):
    """Datos necesarios para registrar un dispositivo."""


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    quantity: int | None = Field(default=None, ge=0)
    unit_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    precio_venta: Decimal | None = Field(default=None, ge=Decimal("0"))
    imei: str | None = Field(default=None, max_length=18)
    serial: str | None = Field(default=None, max_length=120)
    marca: str | None = Field(default=None, max_length=80)
    modelo: str | None = Field(default=None, max_length=120)
    categoria: str | None = Field(default=None, max_length=80)
    condicion: str | None = Field(default=None, max_length=60)
    color: str | None = Field(default=None, max_length=60)
    capacidad_gb: int | None = Field(default=None, ge=0)
    capacidad: str | None = Field(default=None, max_length=80)
    estado_comercial: CommercialState | None = Field(default=None)
    estado: str | None = Field(default=None, max_length=40)
    proveedor: str | None = Field(default=None, max_length=120)
    costo_unitario: Decimal | None = Field(default=None, ge=Decimal("0"))
    costo_compra: Decimal | None = Field(default=None, ge=Decimal("0"))
    margen_porcentaje: Decimal | None = Field(default=None, ge=Decimal("0"))
    garantia_meses: int | None = Field(default=None, ge=0)
    lote: str | None = Field(default=None, max_length=80)
    fecha_compra: date | None = Field(default=None)
    fecha_ingreso: date | None = Field(default=None)
    ubicacion: str | None = Field(default=None, max_length=120)
    descripcion: str | None = Field(default=None, max_length=1024)
    imagen_url: str | None = Field(default=None, max_length=255)

    @model_validator(mode="before")
    @classmethod
    def _map_update_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "precio_venta" in data and "unit_price" not in data:
                data["unit_price"] = data["precio_venta"]
            if "costo_compra" in data and "costo_unitario" not in data:
                data["costo_unitario"] = data["costo_compra"]
        return data

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

    @field_validator(
        "marca",
        "modelo",
        "color",
        "categoria",
        "condicion",
        "capacidad",
        "estado",
        "proveedor",
        "lote",
        "ubicacion",
        "descripcion",
        "imagen_url",
        mode="before",
    )
    @classmethod
    def _normalize_update_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
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
    categoria: str | None = Field(default=None, max_length=80)
    condicion: str | None = Field(default=None, max_length=60)
    estado: str | None = Field(default=None, max_length=40)
    ubicacion: str | None = Field(default=None, max_length=120)
    proveedor: str | None = Field(default=None, max_length=120)
    fecha_ingreso_desde: date | None = Field(default=None)
    fecha_ingreso_hasta: date | None = Field(default=None)

    model_config = ConfigDict(extra="forbid")

    @field_validator("imei", "serial", "color", "marca", "modelo", mode="before")
    @classmethod
    def _normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("categoria", "condicion", "estado", "ubicacion", "proveedor", mode="before")
    @classmethod
    def _normalize_additional_filters(cls, value: str | None) -> str | None:
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


class ContactHistoryEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    note: str = Field(..., min_length=3, max_length=255)

    @field_validator("note")
    @classmethod
    def _normalize_note(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("La nota debe tener al menos 3 caracteres.")
        return normalized

    @field_serializer("timestamp")
    @classmethod
    def _serialize_timestamp(cls, value: datetime) -> str:
        return value.isoformat()


class CustomerBase(BaseModel):
    contact_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=500)
    outstanding_debt: Decimal = Field(default=Decimal("0"))
    history: list[ContactHistoryEntry] = Field(default_factory=list)

    @field_validator("contact_name", "email", "phone", "address", "notes", mode="before")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_serializer("outstanding_debt")
    @classmethod
    def _serialize_debt(cls, value: Decimal) -> float:
        return float(value)


class CustomerCreate(CustomerBase):
    name: str = Field(..., max_length=120)

    @field_validator("name")
    @classmethod
    def _normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El nombre es obligatorio.")
        return normalized


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    contact_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=500)
    outstanding_debt: Decimal | None = Field(default=None)
    history: list[ContactHistoryEntry] | None = Field(default=None)

    @field_validator("name", "contact_name", "email", "phone", "address", "notes", mode="before")
    @classmethod
    def _normalize_update_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CustomerResponse(CustomerBase):
    id: int
    name: str
    last_interaction_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierBase(BaseModel):
    contact_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=500)
    outstanding_debt: Decimal = Field(default=Decimal("0"))
    history: list[ContactHistoryEntry] = Field(default_factory=list)

    @field_validator("contact_name", "email", "phone", "address", "notes", mode="before")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_serializer("outstanding_debt")
    @classmethod
    def _serialize_debt(cls, value: Decimal) -> float:
        return float(value)


class SupplierCreate(SupplierBase):
    name: str = Field(..., max_length=120)

    @field_validator("name")
    @classmethod
    def _normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El nombre es obligatorio.")
        return normalized


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    contact_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=500)
    outstanding_debt: Decimal | None = Field(default=None)
    history: list[ContactHistoryEntry] | None = Field(default=None)

    @field_validator("name", "contact_name", "email", "phone", "address", "notes", mode="before")
    @classmethod
    def _normalize_update_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class SupplierResponse(SupplierBase):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierBatchBase(BaseModel):
    model_name: str = Field(..., max_length=120)
    batch_code: str = Field(..., max_length=80)
    unit_cost: Decimal = Field(..., ge=Decimal("0"))
    quantity: int = Field(default=0, ge=0)
    purchase_date: date
    notes: str | None = Field(default=None, max_length=255)
    store_id: int | None = Field(default=None, ge=1)
    device_id: int | None = Field(default=None, ge=1)

    model_config = ConfigDict(protected_namespaces=())

    @field_validator("model_name", "batch_code", "notes", mode="before")
    @classmethod
    def _normalize_batch_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_serializer("unit_cost")
    @classmethod
    def _serialize_unit_cost(cls, value: Decimal) -> float:
        return float(value)


class SupplierBatchCreate(SupplierBatchBase):
    pass


class SupplierBatchUpdate(BaseModel):
    model_name: str | None = Field(default=None, max_length=120)
    batch_code: str | None = Field(default=None, max_length=80)
    unit_cost: Decimal | None = Field(default=None, ge=Decimal("0"))
    quantity: int | None = Field(default=None, ge=0)
    purchase_date: date | None = None
    notes: str | None = Field(default=None, max_length=255)
    store_id: int | None = Field(default=None, ge=1)
    device_id: int | None = Field(default=None, ge=1)

    @field_validator("model_name", "batch_code", "notes", mode="before")
    @classmethod
    def _normalize_optional_batch_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class SupplierBatchResponse(SupplierBatchBase):
    id: int
    supplier_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierBatchOverviewItem(BaseModel):
    supplier_id: int
    supplier_name: str
    batch_count: int = Field(ge=0)
    total_quantity: int = Field(ge=0)
    total_value: float = Field(ge=0)
    latest_purchase_date: date
    latest_batch_code: str | None = None
    latest_unit_cost: float | None = Field(default=None, ge=0)


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


class UserStatusUpdate(BaseModel):
    is_active: bool


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
    session_id: int
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: int
    jti: str


class TOTPSetupResponse(BaseModel):
    secret: str
    otpauth_url: str


class TOTPActivateRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class TOTPStatusResponse(BaseModel):
    is_active: bool
    activated_at: datetime | None
    last_verified_at: datetime | None


class ActiveSessionResponse(BaseModel):
    id: int
    user_id: int
    session_token: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None
    revoked_by_id: int | None
    revoke_reason: str | None

    model_config = ConfigDict(from_attributes=True)


class SessionRevokeRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=255)


class MovementBase(BaseModel):
    producto_id: int = Field(
        ...,
        ge=1,
        validation_alias=AliasChoices("producto_id", "device_id"),
        serialization_alias="producto_id",
    )
    tipo_movimiento: MovementType = Field(
        ...,
        validation_alias=AliasChoices("tipo_movimiento", "movement_type"),
        serialization_alias="tipo_movimiento",
    )
    cantidad: int = Field(
        ...,
        gt=0,
        validation_alias=AliasChoices("cantidad", "quantity"),
        serialization_alias="cantidad",
    )
    comentario: str | None = Field(
        default=None,
        max_length=255,
        validation_alias=AliasChoices("comentario", "reason", "comment"),
        serialization_alias="comentario",
    )
    tienda_origen_id: int | None = Field(
        default=None,
        ge=1,
        validation_alias=AliasChoices("tienda_origen_id", "source_store_id"),
        serialization_alias="tienda_origen_id",
    )
    tienda_destino_id: int | None = Field(
        default=None,
        ge=1,
        validation_alias=AliasChoices("tienda_destino_id", "store_id", "destination_store_id"),
        serialization_alias="tienda_destino_id",
    )
    unit_cost: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        validation_alias=AliasChoices("unit_cost", "costo_unitario"),
        serialization_alias="unit_cost",
    )


class MovementCreate(MovementBase):
    """Carga de datos para registrar movimientos de inventario."""


class MovementResponse(BaseModel):
    id: int
    producto_id: int = Field(
        validation_alias=AliasChoices("producto_id", "device_id"),
        serialization_alias="producto_id",
    )
    tipo_movimiento: MovementType = Field(
        validation_alias=AliasChoices("tipo_movimiento", "movement_type"),
        serialization_alias="tipo_movimiento",
    )
    cantidad: int = Field(
        validation_alias=AliasChoices("cantidad", "quantity"),
        serialization_alias="cantidad",
    )
    comentario: str | None = Field(
        default=None,
        validation_alias=AliasChoices("comentario", "comment"),
        serialization_alias="comentario",
    )
    tienda_origen_id: int | None = Field(
        default=None,
        validation_alias=AliasChoices("tienda_origen_id", "source_store_id"),
        serialization_alias="tienda_origen_id",
    )
    tienda_destino_id: int | None = Field(
        default=None,
        validation_alias=AliasChoices("tienda_destino_id", "store_id"),
        serialization_alias="tienda_destino_id",
    )
    usuario_id: int | None = Field(
        default=None,
        validation_alias=AliasChoices("usuario_id", "performed_by_id"),
        serialization_alias="usuario_id",
    )
    fecha: datetime = Field(
        validation_alias=AliasChoices("fecha", "created_at"),
        serialization_alias="fecha",
    )
    unit_cost: Decimal | None = Field(default=None)
    store_inventory_value: Decimal

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("unit_cost")
    @classmethod
    def _serialize_unit_cost(cls, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)

    @field_serializer("store_inventory_value")
    @classmethod
    def _serialize_inventory_total(cls, value: Decimal) -> float:
        return float(value)


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


class AuditHighlight(BaseModel):
    id: int
    action: str
    created_at: datetime
    severity: Literal["info", "warning", "critical"]
    entity_type: str
    entity_id: str
    status: Literal["pending", "acknowledged"] = Field(default="pending")
    acknowledged_at: datetime | None = None
    acknowledged_by_id: int | None = None
    acknowledged_by_name: str | None = None
    acknowledged_note: str | None = None

    @field_serializer("created_at")
    @classmethod
    def _serialize_created_at(cls, value: datetime) -> str:
        return value.isoformat()


class AuditAcknowledgedEntity(BaseModel):
    entity_type: str
    entity_id: str
    acknowledged_at: datetime
    acknowledged_by_id: int | None = None
    acknowledged_by_name: str | None = None
    note: str | None = None

    @field_serializer("acknowledged_at")
    @classmethod
    def _serialize_ack_time(cls, value: datetime) -> str:
        return value.isoformat()


class DashboardAuditAlerts(BaseModel):
    total: int
    critical: int
    warning: int
    info: int
    pending_count: int = Field(default=0, ge=0)
    acknowledged_count: int = Field(default=0, ge=0)
    highlights: list[AuditHighlight] = Field(default_factory=list)
    acknowledged_entities: list[AuditAcknowledgedEntity] = Field(default_factory=list)

    @computed_field(return_type=bool)  # type: ignore[misc]
    def has_alerts(self) -> bool:
        return self.critical > 0 or self.warning > 0


class DashboardGlobalMetrics(BaseModel):
    total_sales: float
    sales_count: int
    total_stock: int
    open_repairs: int
    gross_profit: float


class DashboardChartPoint(BaseModel):
    label: str
    value: float


class InventoryMetricsResponse(BaseModel):
    totals: InventoryTotals
    top_stores: list[StoreValueMetric]
    low_stock_devices: list[LowStockDevice]
    global_performance: DashboardGlobalMetrics
    sales_trend: list[DashboardChartPoint] = Field(default_factory=list)
    stock_breakdown: list[DashboardChartPoint] = Field(default_factory=list)
    repair_mix: list[DashboardChartPoint] = Field(default_factory=list)
    profit_breakdown: list[DashboardChartPoint] = Field(default_factory=list)
    audit_alerts: DashboardAuditAlerts


class RotationMetric(BaseModel):
    store_id: int
    store_name: str
    device_id: int
    sku: str
    name: str
    sold_units: int
    received_units: int
    rotation_rate: float


class AnalyticsRotationResponse(BaseModel):
    items: list[RotationMetric]


class AgingMetric(BaseModel):
    device_id: int
    sku: str
    name: str
    store_id: int
    store_name: str
    days_in_stock: int
    quantity: int


class AnalyticsAgingResponse(BaseModel):
    items: list[AgingMetric]


class StockoutForecastMetric(BaseModel):
    device_id: int
    sku: str
    name: str
    store_id: int
    store_name: str
    average_daily_sales: float
    projected_days: int | None
    quantity: int
    trend: str
    trend_score: float
    confidence: float
    alert_level: str | None
    sold_units: int


class AnalyticsForecastResponse(BaseModel):
    items: list[StockoutForecastMetric]


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


class SyncOutboxEntryResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    operation: str
    payload: dict[str, Any]
    attempt_count: int
    last_attempt_at: datetime | None
    status: SyncOutboxStatus
    priority: SyncOutboxPriority
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("payload", mode="before")
    @classmethod
    def _parse_payload(cls, value: Any) -> dict[str, Any]:
        if isinstance(value, str):
            try:
                import json

                return json.loads(value)
            except Exception:  # pragma: no cover - fallback to empty payload
                return {}
        if isinstance(value, dict):
            return value
        return {}


class SyncOutboxStatsEntry(BaseModel):
    entity_type: str
    priority: SyncOutboxPriority
    total: int
    pending: int
    failed: int
    latest_update: datetime | None
    oldest_pending: datetime | None


class SyncSessionCompact(BaseModel):
    id: int
    mode: SyncMode
    status: SyncStatus
    started_at: datetime
    finished_at: datetime | None
    error_message: str | None


class SyncStoreHistory(BaseModel):
    store_id: int | None
    store_name: str
    sessions: list[SyncSessionCompact]


class StoreComparativeMetric(BaseModel):
    store_id: int
    store_name: str
    device_count: int
    total_units: int
    inventory_value: float
    average_rotation: float
    average_aging_days: float
    sales_last_30_days: float
    sales_count_last_30_days: int


class AnalyticsComparativeResponse(BaseModel):
    items: list[StoreComparativeMetric]


class ProfitMarginMetric(BaseModel):
    store_id: int
    store_name: str
    revenue: float
    cost: float
    profit: float
    margin_percent: float


class AnalyticsProfitMarginResponse(BaseModel):
    items: list[ProfitMarginMetric]


class SalesProjectionMetric(BaseModel):
    store_id: int
    store_name: str
    average_daily_units: float
    average_ticket: float
    projected_units: float
    projected_revenue: float
    confidence: float
    trend: str
    trend_score: float
    revenue_trend_score: float
    r2_revenue: float


class AnalyticsSalesProjectionResponse(BaseModel):
    items: list[SalesProjectionMetric]


class AnalyticsAlert(BaseModel):
    type: str
    level: str
    message: str
    store_id: int | None
    store_name: str
    device_id: int | None
    sku: str | None


class AnalyticsAlertsResponse(BaseModel):
    items: list[AnalyticsAlert]


class StoreRealtimeWidget(BaseModel):
    store_id: int
    store_name: str
    inventory_value: float
    sales_today: float
    last_sale_at: datetime | None
    low_stock_devices: int
    pending_repairs: int
    last_sync_at: datetime | None
    trend: str
    trend_score: float
    confidence: float


class AnalyticsRealtimeResponse(BaseModel):
    items: list[StoreRealtimeWidget]


class AnalyticsCategoriesResponse(BaseModel):
    categories: list[str]


class SyncOutboxReplayRequest(BaseModel):
    ids: list[int] = Field(..., min_length=1)


class AuditLogResponse(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: str
    details: str | None
    performed_by_id: int | None
    created_at: datetime
    severity: Literal["info", "warning", "critical"] = Field(default="info")
    severity_label: str = Field(default="Informativa")

    model_config = ConfigDict(from_attributes=True)


class AuditReminderEntry(BaseModel):
    entity_type: str
    entity_id: str
    first_seen: datetime
    last_seen: datetime
    occurrences: int = Field(..., ge=1)
    latest_action: str
    latest_details: str | None = None
    status: Literal["pending", "acknowledged"] = Field(default="pending")
    acknowledged_at: datetime | None = None
    acknowledged_by_id: int | None = None
    acknowledged_by_name: str | None = None
    acknowledged_note: str | None = None

    @field_serializer("first_seen", "last_seen", when_used="json")
    @classmethod
    def _serialize_timestamp(cls, value: datetime) -> str:
        return value.isoformat()

    @field_serializer("acknowledged_at")
    @classmethod
    def _serialize_ack(cls, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class AuditReminderSummary(BaseModel):
    threshold_minutes: int = Field(..., ge=0)
    min_occurrences: int = Field(..., ge=1)
    total: int = Field(..., ge=0)
    pending_count: int = Field(..., ge=0)
    acknowledged_count: int = Field(..., ge=0)
    persistent: list[AuditReminderEntry]


class AuditAcknowledgementCreate(BaseModel):
    entity_type: str = Field(..., min_length=1, max_length=80)
    entity_id: str = Field(..., min_length=1, max_length=80)
    note: str | None = Field(default=None, max_length=255)

    @field_validator("entity_type", "entity_id")
    @classmethod
    def _normalize_identifier(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Valor requerido")
        return normalized

    @field_validator("note")
    @classmethod
    def _normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AuditAcknowledgementResponse(BaseModel):
    entity_type: str
    entity_id: str
    acknowledged_at: datetime
    acknowledged_by_id: int | None = None
    acknowledged_by_name: str | None = None
    note: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("acknowledged_at")
    @classmethod
    def _serialize_acknowledged_at(cls, value: datetime) -> str:
        return value.isoformat()


class PurchaseOrderItemCreate(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity_ordered: int = Field(..., ge=1)
    unit_cost: Decimal = Field(..., ge=Decimal("0"))

    @field_serializer("unit_cost")
    @classmethod
    def _serialize_unit_cost(cls, value: Decimal) -> float:
        return float(value)


class PurchaseOrderCreate(BaseModel):
    store_id: int = Field(..., ge=1)
    supplier: str = Field(..., max_length=120)
    notes: str | None = Field(default=None, max_length=255)
    items: list[PurchaseOrderItemCreate]

    @field_validator("supplier")
    @classmethod
    def _validate_supplier(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Proveedor requerido")
        return normalized

    @field_validator("notes")
    @classmethod
    def _normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("items")
    @classmethod
    def _ensure_items(cls, value: list[PurchaseOrderItemCreate]) -> list[PurchaseOrderItemCreate]:
        if not value:
            raise ValueError("Debes incluir artículos en la orden de compra.")
        return value


class PurchaseOrderItemResponse(BaseModel):
    id: int
    purchase_order_id: int
    device_id: int
    quantity_ordered: int
    quantity_received: int
    unit_cost: Decimal

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("unit_cost")
    @classmethod
    def _serialize_unit_cost(cls, value: Decimal) -> float:
        return float(value)


class PurchaseReturnCreate(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)
    reason: str = Field(..., min_length=5, max_length=255)

    @field_validator("reason")
    @classmethod
    def _normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 5:
            raise ValueError("El motivo debe tener al menos 5 caracteres.")
        return normalized


class PurchaseReturnResponse(BaseModel):
    id: int
    purchase_order_id: int
    device_id: int
    quantity: int
    reason: str
    processed_by_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderResponse(BaseModel):
    id: int
    store_id: int
    supplier: str
    status: PurchaseStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
    created_by_id: int | None
    closed_at: datetime | None
    items: list[PurchaseOrderItemResponse]
    returns: list[PurchaseReturnResponse] = []

    model_config = ConfigDict(from_attributes=True)


class PurchaseReceiveItem(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)


class PurchaseReceiveRequest(BaseModel):
    items: list[PurchaseReceiveItem]

    @field_validator("items")
    @classmethod
    def _ensure_items(cls, value: list[PurchaseReceiveItem]) -> list[PurchaseReceiveItem]:
        if not value:
            raise ValueError("Debes indicar artículos a recibir.")
        return value


class PurchaseImportResponse(BaseModel):
    imported: int = Field(default=0, ge=0)
    orders: list[PurchaseOrderResponse]
    errors: list[str] = Field(default_factory=list)


class RecurringOrderCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    order_type: RecurringOrderType
    payload: dict[str, Any]

    @model_validator(mode="after")
    def _validate_payload(self) -> "RecurringOrderCreate":
        if self.order_type is RecurringOrderType.PURCHASE:
            validated = PurchaseOrderCreate.model_validate(self.payload)
            self.payload = validated.model_dump()
        elif self.order_type is RecurringOrderType.TRANSFER:
            validated = TransferOrderCreate.model_validate(self.payload)
            self.payload = validated.model_dump()
        else:  # pragma: no cover - enum exhaustivo
            raise ValueError("Tipo de orden recurrente no soportado.")
        return self


class RecurringOrderResponse(BaseModel):
    id: int
    name: str
    description: str | None
    order_type: RecurringOrderType
    store_id: int | None
    store_name: str | None = None
    payload: dict[str, Any]
    created_by_id: int | None
    created_by_name: str | None = None
    last_used_by_id: int | None
    last_used_by_name: str | None = None
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None


class RecurringOrderExecutionResult(BaseModel):
    template_id: int
    order_type: RecurringOrderType
    reference_id: int
    store_id: int | None
    created_at: datetime
    summary: str


class OperationHistoryType(str, enum.Enum):
    PURCHASE = "purchase"
    TRANSFER_DISPATCH = "transfer_dispatch"
    TRANSFER_RECEIVE = "transfer_receive"
    SALE = "sale"


class OperationHistoryEntry(BaseModel):
    id: str
    operation_type: OperationHistoryType
    occurred_at: datetime
    store_id: int | None
    store_name: str | None
    technician_id: int | None
    technician_name: str | None
    reference: str | None
    description: str
    amount: Decimal | None = None

    @field_serializer("amount")
    @classmethod
    def _serialize_amount(cls, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)


class OperationHistoryTechnician(BaseModel):
    id: int
    name: str


class OperationsHistoryResponse(BaseModel):
    records: list[OperationHistoryEntry]
    technicians: list[OperationHistoryTechnician]


class RepairOrderPartPayload(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)
    unit_cost: Decimal | None = Field(default=None, ge=Decimal("0"))

    @field_validator("unit_cost")
    @classmethod
    def _normalize_unit_cost(cls, value: Decimal | None) -> Decimal:
        if value is None:
            return Decimal("0")
        return value


class RepairOrderCreate(BaseModel):
    store_id: int = Field(..., ge=1)
    customer_id: int | None = Field(default=None, ge=1)
    customer_name: str | None = Field(default=None, max_length=120)
    technician_name: str = Field(..., max_length=120)
    damage_type: str = Field(..., max_length=120)
    device_description: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=500)
    labor_cost: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    parts: list[RepairOrderPartPayload] = Field(default_factory=list)

    @field_validator(
        "customer_name", "technician_name", "damage_type", "device_description", "notes"
    )
    @classmethod
    def _normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class RepairOrderUpdate(BaseModel):
    customer_id: int | None = Field(default=None, ge=1)
    customer_name: str | None = Field(default=None, max_length=120)
    technician_name: str | None = Field(default=None, max_length=120)
    damage_type: str | None = Field(default=None, max_length=120)
    device_description: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=500)
    status: RepairStatus | None = None
    labor_cost: Decimal | None = Field(default=None, ge=Decimal("0"))
    parts: list[RepairOrderPartPayload] | None = None

    @field_validator(
        "customer_name",
        "technician_name",
        "damage_type",
        "device_description",
        "notes",
        mode="before",
    )
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class RepairOrderPartResponse(BaseModel):
    id: int
    repair_order_id: int
    device_id: int
    quantity: int
    unit_cost: Decimal

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("unit_cost")
    @classmethod
    def _serialize_unit_cost(cls, value: Decimal) -> float:
        return float(value)


class RepairOrderResponse(BaseModel):
    id: int
    store_id: int
    customer_id: int | None
    customer_name: str | None
    technician_name: str
    damage_type: str
    device_description: str | None
    notes: str | None
    status: RepairStatus
    labor_cost: Decimal
    parts_cost: Decimal
    total_cost: Decimal
    inventory_adjusted: bool
    opened_at: datetime
    updated_at: datetime
    delivered_at: datetime | None
    parts: list[RepairOrderPartResponse]

    model_config = ConfigDict(from_attributes=True)

    @computed_field(return_type=str)  # type: ignore[misc]
    def status_color(self) -> str:
        mapping = {
            RepairStatus.PENDIENTE: "🟡",
            RepairStatus.EN_PROCESO: "🟠",
            RepairStatus.LISTO: "🟢",
            RepairStatus.ENTREGADO: "⚪",
        }
        return mapping.get(self.status, "⬜")

    @field_serializer("labor_cost", "parts_cost", "total_cost")
    @classmethod
    def _serialize_cost(cls, value: Decimal) -> float:
        return float(value)


class SaleItemCreate(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)
    discount_percent: Decimal | None = Field(
        default=Decimal("0"), ge=Decimal("0"), le=Decimal("100")
    )

    @field_validator("discount_percent")
    @classmethod
    def _normalize_discount(cls, value: Decimal | None) -> Decimal:
        if value is None:
            return Decimal("0")
        return value


class SaleCreate(BaseModel):
    store_id: int = Field(..., ge=1)
    customer_id: int | None = Field(default=None, ge=1)
    customer_name: str | None = Field(default=None, max_length=120)
    payment_method: PaymentMethod = Field(default=PaymentMethod.EFECTIVO)
    discount_percent: Decimal | None = Field(default=Decimal("0"), ge=Decimal("0"), le=Decimal("100"))
    notes: str | None = Field(default=None, max_length=255)
    items: list[SaleItemCreate]

    @field_validator("customer_name")
    @classmethod
    def _normalize_customer(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("notes")
    @classmethod
    def _normalize_sale_notes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("items")
    @classmethod
    def _ensure_sale_items(cls, value: list[SaleItemCreate]) -> list[SaleItemCreate]:
        if not value:
            raise ValueError("Debes agregar artículos a la venta.")
        return value


class SaleItemResponse(BaseModel):
    id: int
    sale_id: int
    device_id: int
    quantity: int
    unit_price: Decimal
    discount_amount: Decimal
    total_line: Decimal

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("unit_price", "discount_amount", "total_line")
    @classmethod
    def _serialize_amount(cls, value: Decimal) -> float:
        return float(value)


class SaleCustomerSummary(BaseModel):
    id: int
    name: str
    outstanding_debt: Decimal

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("outstanding_debt")
    @classmethod
    def _serialize_debt(cls, value: Decimal) -> float:
        return float(value)


class CashSessionSummary(BaseModel):
    id: int
    status: CashSessionStatus
    opened_at: datetime
    closed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SaleResponse(BaseModel):
    id: int
    store_id: int
    customer_id: int | None
    customer_name: str | None
    payment_method: PaymentMethod
    discount_percent: Decimal
    subtotal_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    notes: str | None
    created_at: datetime
    performed_by_id: int | None
    cash_session_id: int | None
    customer: SaleCustomerSummary | None = None
    cash_session: CashSessionSummary | None = None
    items: list[SaleItemResponse]
    returns: list["SaleReturnResponse"] = []

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("discount_percent", "subtotal_amount", "tax_amount", "total_amount")
    @classmethod
    def _serialize_sale_amount(cls, value: Decimal) -> float:
        return float(value)


class SaleReturnItem(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)
    reason: str = Field(..., min_length=5, max_length=255)

    @field_validator("reason")
    @classmethod
    def _normalize_sale_reason(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 5:
            raise ValueError("El motivo debe tener al menos 5 caracteres.")
        return normalized


class SaleReturnCreate(BaseModel):
    sale_id: int = Field(..., ge=1)
    items: list[SaleReturnItem]

    @field_validator("items")
    @classmethod
    def _ensure_return_items(cls, value: list[SaleReturnItem]) -> list[SaleReturnItem]:
        if not value:
            raise ValueError("Debes indicar artículos a devolver.")
        return value


class SaleReturnResponse(BaseModel):
    id: int
    sale_id: int
    device_id: int
    quantity: int
    reason: str
    processed_by_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class POSCartItem(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)
    discount_percent: Decimal | None = Field(
        default=Decimal("0"), ge=Decimal("0"), le=Decimal("100")
    )

    @field_validator("discount_percent")
    @classmethod
    def _normalize_pos_discount(cls, value: Decimal | None) -> Decimal:
        if value is None:
            return Decimal("0")
        return value


class POSSaleRequest(BaseModel):
    store_id: int = Field(..., ge=1)
    customer_id: int | None = Field(default=None, ge=1)
    customer_name: str | None = Field(default=None, max_length=120)
    payment_method: PaymentMethod = Field(default=PaymentMethod.EFECTIVO)
    discount_percent: Decimal | None = Field(
        default=Decimal("0"), ge=Decimal("0"), le=Decimal("100")
    )
    notes: str | None = Field(default=None, max_length=255)
    items: list[POSCartItem]
    draft_id: int | None = Field(default=None, ge=1)
    save_as_draft: bool = Field(default=False)
    confirm: bool = Field(default=False)
    apply_taxes: bool = Field(default=True)
    cash_session_id: int | None = Field(default=None, ge=1)
    payment_breakdown: dict[str, Decimal] = Field(default_factory=dict)

    @field_validator("customer_name")
    @classmethod
    def _normalize_pos_customer(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("notes")
    @classmethod
    def _normalize_pos_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("items")
    @classmethod
    def _ensure_pos_items(cls, value: list[POSCartItem]) -> list[POSCartItem]:
        if not value:
            raise ValueError("Debes agregar dispositivos al carrito.")
        return value

    @field_validator("payment_breakdown", mode="before")
    @classmethod
    def _normalize_breakdown(cls, value: dict[str, Decimal] | None) -> dict[str, Decimal]:
        if value is None:
            return {}
        normalized: dict[str, Decimal] = {}
        for method_key, amount in value.items():
            method = method_key.strip().upper()
            try:
                PaymentMethod(method)
            except ValueError as exc:  # pragma: no cover - validation error path
                raise ValueError("Método de pago inválido en el desglose.") from exc
            normalized[method] = Decimal(str(amount))
        return normalized


class POSDraftResponse(BaseModel):
    id: int
    store_id: int
    payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class POSSaleResponse(BaseModel):
    status: Literal["draft", "registered"]
    sale: SaleResponse | None = None
    draft: POSDraftResponse | None = None
    receipt_url: str | None = None
    warnings: list[str] = Field(default_factory=list)
    cash_session_id: int | None = None
    payment_breakdown: dict[str, float] = Field(default_factory=dict)

    @field_serializer("payment_breakdown")
    @classmethod
    def _serialize_breakdown(cls, value: dict[str, float]) -> dict[str, float]:
        return {key: float(amount) for key, amount in value.items()}


class CashSessionOpenRequest(BaseModel):
    store_id: int = Field(..., ge=1)
    opening_amount: Decimal = Field(..., ge=Decimal("0"))
    notes: str | None = Field(default=None, max_length=255)

    @field_validator("notes")
    @classmethod
    def _normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CashSessionCloseRequest(BaseModel):
    session_id: int = Field(..., ge=1)
    closing_amount: Decimal = Field(..., ge=Decimal("0"))
    notes: str | None = Field(default=None, max_length=255)
    payment_breakdown: dict[str, Decimal] = Field(default_factory=dict)

    @field_validator("notes")
    @classmethod
    def _normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("payment_breakdown", mode="before")
    @classmethod
    def _normalize_breakdown(cls, value: dict[str, Decimal] | None) -> dict[str, Decimal]:
        if value is None:
            return {}
        normalized: dict[str, Decimal] = {}
        for method_key, amount in value.items():
            method = method_key.strip().upper()
            try:
                PaymentMethod(method)
            except ValueError as exc:
                raise ValueError("Método de pago inválido.") from exc
            normalized[method] = Decimal(str(amount))
        return normalized


class CashSessionResponse(BaseModel):
    id: int
    store_id: int
    status: CashSessionStatus
    opening_amount: Decimal
    closing_amount: Decimal
    expected_amount: Decimal
    difference_amount: Decimal
    payment_breakdown: dict[str, float]
    notes: str | None
    opened_by_id: int | None
    closed_by_id: int | None
    opened_at: datetime
    closed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer(
        "opening_amount",
        "closing_amount",
        "expected_amount",
        "difference_amount",
    )
    @classmethod
    def _serialize_amount(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("payment_breakdown")
    @classmethod
    def _serialize_breakdown(cls, value: dict[str, float]) -> dict[str, float]:
        return {key: float(amount) for key, amount in value.items()}


class POSConfigResponse(BaseModel):
    store_id: int
    tax_rate: Decimal
    invoice_prefix: str
    printer_name: str | None
    printer_profile: str | None
    quick_product_ids: list[int]
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("tax_rate")
    @classmethod
    def _serialize_tax(cls, value: Decimal) -> float:
        return float(value)


class POSConfigUpdate(BaseModel):
    store_id: int = Field(..., ge=1)
    tax_rate: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))
    invoice_prefix: str = Field(..., min_length=1, max_length=12)
    printer_name: str | None = Field(default=None, max_length=120)
    printer_profile: str | None = Field(default=None, max_length=255)
    quick_product_ids: list[int] = Field(default_factory=list)

    @field_validator("quick_product_ids")
    @classmethod
    def _validate_quick_products(cls, value: list[int]) -> list[int]:
        normalized = []
        for item in value:
            if int(item) < 1:
                raise ValueError("Los identificadores rápidos deben ser positivos.")
            normalized.append(int(item))
        return normalized

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
    "AgingMetric",
    "AnalyticsAgingResponse",
    "AnalyticsComparativeResponse",
    "AnalyticsForecastResponse",
    "AnalyticsProfitMarginResponse",
    "AnalyticsRotationResponse",
    "AnalyticsSalesProjectionResponse",
    "AuditAcknowledgedEntity",
    "AuditAcknowledgementCreate",
    "AuditAcknowledgementResponse",
    "AuditHighlight",
    "AuditLogResponse",
    "AuditReminderEntry",
    "AuditReminderSummary",
    "DashboardAuditAlerts",
    "BackupJobResponse",
    "BackupRunRequest",
    "DeviceBase",
    "DeviceCreate",
    "DeviceResponse",
    "DeviceUpdate",
    "InventoryMetricsResponse",
    "InventorySummary",
    "DashboardChartPoint",
    "DashboardGlobalMetrics",
    "InventoryTotals",
    "LowStockDevice",
    "MovementBase",
    "MovementCreate",
    "MovementResponse",
    "PurchaseOrderCreate",
    "PurchaseOrderItemCreate",
    "PurchaseOrderItemResponse",
    "PurchaseOrderResponse",
    "PurchaseReceiveItem",
    "PurchaseReceiveRequest",
    "PurchaseImportResponse",
    "PurchaseReturnCreate",
    "PurchaseReturnResponse",
    "RecurringOrderCreate",
    "RecurringOrderExecutionResult",
    "RecurringOrderResponse",
    "OperationHistoryEntry",
    "OperationHistoryTechnician",
    "OperationHistoryType",
    "OperationsHistoryResponse",
    "SaleCreate",
    "SaleItemCreate",
    "SaleItemResponse",
    "SaleResponse",
    "SaleReturnCreate",
    "SaleReturnItem",
    "SaleReturnResponse",
    "POSCartItem",
    "POSSaleRequest",
    "POSSaleResponse",
    "POSDraftResponse",
    "POSConfigResponse",
    "POSConfigUpdate",
    "ReleaseInfo",
    "RoleResponse",
    "StoreBase",
    "StoreCreate",
    "StoreResponse",
    "StoreUpdate",
    "StoreValueMetric",
    "StoreComparativeMetric",
    "SupplierBase",
    "SupplierBatchBase",
    "SupplierBatchCreate",
    "SupplierBatchOverviewItem",
    "SupplierBatchResponse",
    "SupplierBatchUpdate",
    "SupplierCreate",
    "SupplierResponse",
    "SupplierUpdate",
    "SyncRequest",
    "SyncOutboxEntryResponse",
    "SyncOutboxPriority",
    "SyncOutboxStatsEntry",
    "SyncSessionCompact",
    "SyncStoreHistory",
    "SyncOutboxReplayRequest",
    "SyncSessionResponse",
    "TokenPayload",
    "TokenResponse",
    "UpdateStatus",
    "UserBase",
    "UserCreate",
    "UserResponse",
    "UserRolesUpdate",
    "UserStatusUpdate",
    "ProfitMarginMetric",
    "RotationMetric",
    "SalesProjectionMetric",
    "StockoutForecastMetric",
]
