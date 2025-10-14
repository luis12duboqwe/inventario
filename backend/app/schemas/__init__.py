"""Esquemas Pydantic centralizados para la API de Softmobile Central."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_serializer, field_validator

from ..models import (
    BackupMode,
    CashSessionStatus,
    CommercialState,
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
    store_name: str
    average_daily_sales: float
    projected_days: int | None
    quantity: int


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


class AnalyticsSalesProjectionResponse(BaseModel):
    items: list[SalesProjectionMetric]


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

    model_config = ConfigDict(from_attributes=True)


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
    "AuditLogResponse",
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
    "PurchaseReturnCreate",
    "PurchaseReturnResponse",
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
