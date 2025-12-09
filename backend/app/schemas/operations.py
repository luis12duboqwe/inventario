from __future__ import annotations
import enum
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from ..models import (
    RecurringOrderType,
    ReturnReasonCategory,
    ReturnDisposition,
    PaymentMethod,
)
from .purchases import PurchaseOrderCreate
from .transfers import TransferOrderCreate


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


class ReturnRecordType(str, enum.Enum):
    PURCHASE = "purchase"
    SALE = "sale"


class RMAStatus(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    AUTORIZADA = "AUTORIZADA"
    EN_PROCESO = "EN_PROCESO"
    CERRADA = "CERRADA"


class RMAHistoryEntry(BaseModel):
    id: int
    status: RMAStatus
    message: str | None = None
    created_at: datetime
    created_by_id: int | None = None


class RMACreate(BaseModel):
    sale_return_id: int | None = Field(default=None, ge=1)
    purchase_return_id: int | None = Field(default=None, ge=1)
    disposition: ReturnDisposition = ReturnDisposition.VENDIBLE
    notes: str | None = Field(default=None, max_length=500)
    repair_order_id: int | None = Field(default=None, ge=1)
    replacement_sale_id: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _validate_source(self) -> "RMACreate":
        if not self.sale_return_id and not self.purchase_return_id:
            raise ValueError(
                "Debe especificar una devolución de venta o compra.")
        if self.sale_return_id and self.purchase_return_id:
            raise ValueError(
                "No puede especificar devolución de venta y compra simultáneamente.")
        return self


class RMAUpdate(BaseModel):
    status: RMAStatus | None = None
    notes: str | None = Field(default=None, max_length=500)
    resolution: str | None = Field(default=None, max_length=500)
    disposition: ReturnDisposition | None = None
    repair_order_id: int | None = Field(default=None, ge=1)
    replacement_sale_id: int | None = Field(default=None, ge=1)


class RMARecord(BaseModel):
    id: int
    status: RMAStatus
    sale_return_id: int | None
    purchase_return_id: int | None
    store_id: int | None = None
    device_id: int | None = None
    disposition: ReturnDisposition
    notes: str | None
    repair_order_id: int | None = None
    replacement_sale_id: int | None = None
    history: list[RMAHistoryEntry] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ReturnRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: ReturnRecordType
    reference_id: int
    reference_label: str
    store_id: int
    store_name: str | None = None
    warehouse_id: int | None = None
    warehouse_name: str | None = None
    device_id: int
    device_name: str | None = None
    quantity: int
    reason: str
    reason_category: ReturnReasonCategory = ReturnReasonCategory.OTRO
    disposition: ReturnDisposition = ReturnDisposition.VENDIBLE
    processed_by_id: int | None = None
    processed_by_name: str | None = None
    approved_by_id: int | None = None
    approved_by_name: str | None = None
    partner_name: str | None = None
    occurred_at: datetime
    refund_amount: Decimal | None = None
    payment_method: PaymentMethod | None = None
    corporate_reason: str | None = None
    credit_note_amount: Decimal | None = None

    @field_serializer("refund_amount")
    @classmethod
    def _serialize_refund_amount(cls, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)

    @field_serializer("credit_note_amount")
    @classmethod
    def _serialize_credit_note(cls, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)


class ReturnsTotals(BaseModel):
    total: int
    sales: int
    purchases: int
    refunds_by_method: dict[str, Decimal] = Field(default_factory=dict)
    refund_total_amount: Decimal = Field(default=Decimal("0"))
    credit_notes_total: Decimal = Field(default=Decimal("0"))
    categories: dict[str, int] = Field(default_factory=dict)

    @field_serializer("refunds_by_method")
    @classmethod
    def _serialize_refunds(cls, value: dict[str, Decimal]) -> dict[str, float]:
        return {key: float(amount) for key, amount in value.items()}

    @field_serializer("refund_total_amount")
    @classmethod
    def _serialize_refund_total(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("credit_notes_total")
    @classmethod
    def _serialize_credit_total(cls, value: Decimal) -> float:
        return float(value)


class ReturnsOverview(BaseModel):
    items: list[ReturnRecord]
    totals: ReturnsTotals


class RMAHistoryEntry(BaseModel):
    id: int
    status: RMAStatus
    message: str | None = None
    created_at: datetime
    created_by_id: int | None = None
    created_by_name: str | None = None
