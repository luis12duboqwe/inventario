"""Esquemas para el módulo de transferencias entre sucursales."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, AliasChoices, field_validator

from backend.app.models import TransferStatus
from .audit import AuditTrailInfo


class TransferOrderItemBase(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)
    reservation_id: int | None = Field(default=None, ge=1)


class TransferReceptionItem(BaseModel):
    item_id: int = Field(
        ...,
        ge=1,
        validation_alias=AliasChoices("item_id", "device_id"),
    )
    received_quantity: int = Field(
        default=0,
        ge=0,
        validation_alias=AliasChoices("received_quantity", "quantity"),
    )


class TransferOrderItemCreate(TransferOrderItemBase):
    """Elemento incluido en la creación de una orden de transferencia."""


class TransferOrderTransition(BaseModel):
    reason: str | None = Field(default=None, max_length=255)
    items: list[TransferReceptionItem] | None = None


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
            raise ValueError(
                "Debes incluir al menos un dispositivo en la transferencia.")
        return value


class TransferOrderItemResponse(TransferOrderItemBase):
    id: int
    transfer_order_id: int
    dispatched_quantity: int
    received_quantity: int
    dispatched_unit_cost: Decimal | None = Field(default=None, ge=0)
    device_name: str
    sku: str

    model_config = ConfigDict(from_attributes=True)


class TransferOrderResponse(BaseModel):
    id: int
    origin_store_id: int
    destination_store_id: int
    origin_store_name: str
    destination_store_name: str
    status: TransferStatus
    reason: str | None
    created_at: datetime
    updated_at: datetime
    dispatched_at: datetime | None
    received_at: datetime | None
    cancelled_at: datetime | None
    items: list[TransferOrderItemResponse]
    ultima_accion: AuditTrailInfo | None = None

    model_config = ConfigDict(from_attributes=True)


class TransferReportFilters(BaseModel):
    store_id: int | None = None
    origin_store_id: int | None = None
    destination_store_id: int | None = None
    status: TransferStatus | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class TransferReportDevice(BaseModel):
    sku: str | None
    name: str | None
    quantity: int


class TransferReportItem(BaseModel):
    id: int
    folio: str
    origin_store: str
    destination_store: str
    status: TransferStatus
    reason: str | None
    requested_at: datetime
    dispatched_at: datetime | None
    received_at: datetime | None
    cancelled_at: datetime | None
    requested_by: str | None
    dispatched_by: str | None
    received_by: str | None
    cancelled_by: str | None
    total_quantity: int
    devices: list[TransferReportDevice]
    ultima_accion: AuditTrailInfo | None = None


class TransferReportTotals(BaseModel):
    total_transfers: int
    pending: int
    in_transit: int
    completed: int
    cancelled: int
    total_quantity: int


class TransferReport(BaseModel):
    generated_at: datetime
    filters: TransferReportFilters
    totals: TransferReportTotals
    items: list[TransferReportItem]
