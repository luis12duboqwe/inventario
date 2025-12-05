from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
import enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_serializer,
    field_validator,
    model_validator,
)

from ..models import PurchaseStatus
from .common import DashboardChartPoint


class PurchaseOrderItemCreate(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity_ordered: int = Field(..., ge=1)
    unit_cost: Decimal = Field(..., ge=Decimal("0"))

    @field_serializer("unit_cost")
    @classmethod
    def _serialize_unit_cost(cls, value: Decimal) -> float:
        return float(value)


class PurchaseOrderCreate(BaseModel):
    store_id: int = Field(..., ge=1)  # // [PACK30-31-BACKEND]
    supplier: str = Field(..., max_length=120)
    notes: str | None = Field(default=None, max_length=255)
    items: list[PurchaseOrderItemCreate]

    @model_validator(mode="before")
    @classmethod
    def _coerce_store_alias(cls, data: Any) -> Any:  # pragma: no cover - mapeo directo
        if isinstance(data, dict) and "store_id" not in data:
            for k in ("branch_id",):
                if k in data:
                    data["store_id"] = data[k]
                    break
        return data

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
    quantity_pending: int = 0

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("unit_cost")
    @classmethod
    def _serialize_unit_cost(cls, value: Decimal) -> float:
        return float(value)

    @model_validator(mode="before")
    @classmethod
    def _add_pending(cls, value: Any) -> Any:
        if isinstance(value, dict):
            quantity_ordered = int(value.get("quantity_ordered", 0) or 0)
            quantity_received = int(value.get("quantity_received", 0) or 0)
            value.setdefault("quantity_pending", max(
                quantity_ordered - quantity_received, 0))
            return value

        quantity_ordered = getattr(value, "quantity_ordered", 0) or 0
        quantity_received = getattr(value, "quantity_received", 0) or 0
        setattr(value, "quantity_pending", max(
            quantity_ordered - quantity_received, 0))
        return value


class ReturnDisposition(str, enum.Enum):
    VENDIBLE = "vendible"
    DEFECTUOSO = "defectuoso"
    NO_VENDIBLE = "no_vendible"
    REPARACION = "reparacion"


class ReturnReasonCategory(str, enum.Enum):
    DEFECTO = "defecto"
    LOGISTICA = "logistica"
    CLIENTE = "cliente"
    PRECIO = "precio"
    OTRO = "otro"


class PurchaseReturnCreate(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)
    reason: str = Field(..., min_length=5, max_length=255)
    disposition: ReturnDisposition = Field(
        default=ReturnDisposition.DEFECTUOSO
    )
    warehouse_id: int | None = Field(default=None, ge=1)
    category: ReturnReasonCategory = Field(
        default=ReturnReasonCategory.DEFECTO
    )

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
    reason_category: ReturnReasonCategory
    disposition: ReturnDisposition
    warehouse_id: int | None
    supplier_ledger_entry_id: int | None = None
    corporate_reason: str | None = None
    credit_note_amount: Decimal = Field(default=Decimal("0"))
    processed_by_id: int | None
    approved_by_id: int | None
    approved_by_name: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("credit_note_amount")
    @classmethod
    def _serialize_credit_amount(cls, value: Decimal) -> float:
        return float(value)


class PurchaseOrderDocumentResponse(BaseModel):
    id: int
    purchase_order_id: int
    filename: str
    content_type: str
    storage_backend: str
    uploaded_at: datetime
    uploaded_by_id: int | None
    download_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderStatusEventResponse(BaseModel):
    id: int
    purchase_order_id: int
    status: PurchaseStatus
    note: str | None
    created_at: datetime
    created_by_id: int | None
    created_by_name: str | None = None

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
    approved_by_id: int | None = None
    approved_by_name: str | None = None
    requires_approval: bool = False
    closed_at: datetime | None
    items: list[PurchaseOrderItemResponse]
    pending_items: int = 0
    returns: list[PurchaseReturnResponse] = Field(default_factory=list)
    documents: list[PurchaseOrderDocumentResponse] = Field(
        default_factory=list)
    status_history: list[PurchaseOrderStatusEventResponse] = Field(
        default_factory=list, validation_alias="status_events"
    )

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _compute_pending_items(cls, value: Any) -> Any:
        data = dict(value) if isinstance(value, dict) else value
        items = data.get("items") if isinstance(
            data, dict) else getattr(data, "items", [])
        pending_total = 0
        for item in items or []:
            quantity_ordered = item.get("quantity_ordered") if isinstance(
                item, dict) else getattr(item, "quantity_ordered", 0)
            quantity_received = item.get("quantity_received") if isinstance(
                item, dict) else getattr(item, "quantity_received", 0)
            pending_total += max(int(quantity_ordered or 0) -
                                 int(quantity_received or 0), 0)

        if isinstance(data, dict):
            data.setdefault("pending_items", pending_total)
            return data

        setattr(data, "pending_items", pending_total)
        return data


class PurchaseOrderStatusUpdateRequest(BaseModel):
    status: PurchaseStatus
    note: str | None = Field(default=None, max_length=255)


class PurchaseOrderEmailRequest(BaseModel):
    recipients: list[str] = Field(..., min_length=1)
    message: str | None = Field(default=None, max_length=500)
    include_documents: bool = False


class PurchaseReceiveItem(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)
    batch_code: str | None = Field(default=None, max_length=80)

    @field_validator("batch_code")
    @classmethod
    def _normalize_batch_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


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


class PurchaseSuggestionItem(BaseModel):
    store_id: int
    store_name: str
    supplier_id: int | None
    supplier_name: str | None
    device_id: int
    sku: str
    name: str
    current_quantity: int
    minimum_stock: int
    suggested_quantity: int
    average_daily_sales: float
    projected_coverage_days: int | None
    last_30_days_sales: int
    unit_cost: Decimal = Field(default=Decimal("0"))
    reason: Literal["below_minimum", "projected_consumption"]

    @field_serializer("unit_cost")
    @classmethod
    def _serialize_unit_cost(cls, value: Decimal) -> float:
        return float(value)

    @computed_field(return_type=float)  # type: ignore[misc]
    def suggested_value(self) -> float:
        return float(self.unit_cost * Decimal(self.suggested_quantity))


class PurchaseSuggestionStore(BaseModel):
    store_id: int
    store_name: str
    total_suggested: int
    total_value: float
    items: list[PurchaseSuggestionItem]


class PurchaseSuggestionsResponse(BaseModel):
    generated_at: datetime
    lookback_days: int
    planning_horizon_days: int
    minimum_stock: int
    total_items: int
    stores: list[PurchaseSuggestionStore]


class PurchaseVendorBase(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=150)
    telefono: str | None = Field(default=None, max_length=40)
    correo: str | None = Field(default=None, max_length=120)
    direccion: str | None = Field(default=None, max_length=255)
    tipo: str | None = Field(default=None, max_length=60)
    notas: str | None = Field(default=None, max_length=255)

    @field_validator("nombre")
    @classmethod
    def _normalize_nombre(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("El nombre del proveedor es obligatorio.")
        return normalized

    @field_validator("telefono", "correo", "direccion", "tipo", "notas")
    @classmethod
    def _normalize_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class PurchaseVendorCreate(PurchaseVendorBase):
    estado: str = Field(default="activo", max_length=40)


class PurchaseVendorUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=3, max_length=150)
    telefono: str | None = Field(default=None, max_length=40)
    correo: str | None = Field(default=None, max_length=120)
    direccion: str | None = Field(default=None, max_length=255)
    tipo: str | None = Field(default=None, max_length=60)
    notas: str | None = Field(default=None, max_length=255)
    estado: str | None = Field(default=None, max_length=40)

    @field_validator("nombre", "telefono", "correo", "direccion", "tipo", "notas", "estado")
    @classmethod
    def _normalize_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class PurchaseVendorResponse(PurchaseVendorBase):
    id: int = Field(alias="id_proveedor")
    estado: str
    total_compras: Decimal = Field(default=Decimal("0"))
    total_impuesto: Decimal = Field(default=Decimal("0"))
    compras_registradas: int = Field(default=0, ge=0)
    ultima_compra: datetime | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("total_compras", "total_impuesto")
    @classmethod
    def _serialize_decimal(cls, value: Decimal) -> float:
        return float(value)


class PurchaseVendorStatusUpdate(BaseModel):
    estado: Literal["activo", "inactivo"]


class PurchaseRecordItemBase(BaseModel):
    producto_id: int = Field(..., ge=1)
    cantidad: int = Field(..., ge=1)
    costo_unitario: Decimal = Field(..., ge=Decimal("0"))

    @field_serializer("costo_unitario")
    @classmethod
    def _serialize_cost(cls, value: Decimal) -> float:
        return float(value)


class PurchaseRecordItemCreate(PurchaseRecordItemBase):
    """Detalle de ítems utilizados al registrar una compra."""


class PurchaseRecordItemResponse(PurchaseRecordItemBase):
    id: int = Field(alias="id_detalle")
    subtotal: Decimal = Field(default=Decimal("0"))
    producto_nombre: str | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("subtotal")
    @classmethod
    def _serialize_subtotal(cls, value: Decimal) -> float:
        return float(value)


class PurchaseRecordCreate(BaseModel):
    proveedor_id: int = Field(..., ge=1)
    fecha: datetime | None = None
    forma_pago: str = Field(..., max_length=60)
    estado: str = Field(default="REGISTRADA", max_length=40)
    impuesto_tasa: Decimal = Field(default=Decimal(
        "0.16"), ge=Decimal("0"), le=Decimal("1"))
    items: list[PurchaseRecordItemCreate]

    @field_validator("items")
    @classmethod
    def _ensure_items(cls, value: list[PurchaseRecordItemCreate]) -> list[PurchaseRecordItemCreate]:
        if not value:
            raise ValueError("Debes agregar productos a la compra.")
        return value


class PurchaseRecordResponse(BaseModel):
    id: int = Field(alias="id_compra")
    proveedor_id: int
    proveedor_nombre: str
    usuario_id: int
    usuario_nombre: str | None = None
    fecha: datetime
    forma_pago: str
    estado: str
    subtotal: Decimal
    impuesto: Decimal
    total: Decimal
    items: list[PurchaseRecordItemResponse]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("subtotal", "impuesto", "total")
    @classmethod
    def _serialize_amount(cls, value: Decimal) -> float:
        return float(value)


class PurchaseVendorHistory(BaseModel):
    proveedor: PurchaseVendorResponse
    compras: list[PurchaseRecordResponse]
    total: Decimal
    impuesto: Decimal
    registros: int

    @field_serializer("total", "impuesto")
    @classmethod
    def _serialize_totals(cls, value: Decimal) -> float:
        return float(value)


class PurchaseReportFilters(BaseModel):
    proveedor_id: int | None = None
    usuario_id: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    estado: str | None = None
    query: str | None = None


class PurchaseReportTotals(BaseModel):
    count: int = Field(default=0, ge=0)
    subtotal: Decimal = Field(default=Decimal("0"))
    impuesto: Decimal = Field(default=Decimal("0"))
    total: Decimal = Field(default=Decimal("0"))

    @field_serializer("subtotal", "impuesto", "total")
    @classmethod
    def _serialize_decimal(cls, value: Decimal) -> float:
        return float(value)


class PurchaseReportItem(BaseModel):
    compra_id: int
    folio: str
    proveedor_nombre: str
    usuario_nombre: str | None
    forma_pago: str
    estado: str
    subtotal: Decimal
    impuesto: Decimal
    total: Decimal
    fecha: datetime
    items: list[PurchaseRecordItemResponse]

    @field_serializer("subtotal", "impuesto", "total")
    @classmethod
    def _serialize_decimal(cls, value: Decimal) -> float:
        return float(value)


class PurchaseReport(BaseModel):
    generated_at: datetime
    filters: PurchaseReportFilters
    totals: PurchaseReportTotals
    daily_stats: list[DashboardChartPoint]
    items: list[PurchaseReportItem]


class PurchaseVendorRanking(BaseModel):
    vendor_id: int
    vendor_name: str
    total: Decimal
    orders: int

    @field_serializer("total")
    @classmethod
    def _serialize_total(cls, value: Decimal) -> float:
        return float(value)


class PurchaseUserRanking(BaseModel):
    user_id: int
    user_name: str | None
    total: Decimal
    orders: int

    @field_serializer("total")
    @classmethod
    def _serialize_total(cls, value: Decimal) -> float:
        return float(value)


class PurchaseStatistics(BaseModel):
    monthly_total: Decimal
    monthly_count: int
    top_vendors: list[PurchaseVendorRanking]
    top_users: list[PurchaseUserRanking]
    daily_average: Decimal

    @field_serializer("monthly_total", "daily_average")
    @classmethod
    def _serialize_totals(cls, value: Decimal) -> float:
        return float(value)
