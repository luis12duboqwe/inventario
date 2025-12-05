from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, ConfigDict, model_validator, field_serializer

from ..models import InventoryState
from .devices import DeviceResponse
from .movements import MovementResponse
from .transfers import TransferOrderResponse


class InventoryReservationCreate(BaseModel):
    store_id: int = Field(..., ge=1)
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)
    expires_at: datetime


class InventoryReceivingDistribution(BaseModel):
    store_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)


class InventoryReceivingLine(BaseModel):
    device_id: int | None = Field(default=None, ge=1)
    imei: str | None = Field(default=None, min_length=3, max_length=64)
    serial: str | None = Field(default=None, min_length=3, max_length=64)
    quantity: int = Field(..., ge=1)
    unit_cost: Decimal | None = Field(default=None, ge=Decimal("0"))
    comment: str | None = Field(default=None, min_length=5, max_length=255)
    distributions: list[InventoryReceivingDistribution] | None = None

    @model_validator(mode="after")
    def _ensure_identifier(self) -> "InventoryReceivingLine":
        if self.device_id is None and not (self.imei or self.serial):
            raise ValueError(
                "Cada línea debe incluir `device_id`, `imei` o `serial`."
            )
        if self.distributions:
            store_ids: set[int] = set()
            total_assigned = 0
            for allocation in self.distributions:
                if allocation.store_id in store_ids:
                    raise ValueError(
                        "Cada sucursal destino debe aparecer solo una vez por línea."
                    )
                store_ids.add(allocation.store_id)
                total_assigned += allocation.quantity
            if total_assigned > self.quantity:
                raise ValueError(
                    "La cantidad distribuida excede la recepción capturada."
                )
            if (self.imei or self.serial) and self.distributions:
                if len(self.distributions) != 1:
                    raise ValueError(
                        "Los dispositivos con IMEI o serie solo pueden asignarse a una sucursal."
                    )
                if self.distributions[0].quantity != self.quantity:
                    raise ValueError(
                        "Los dispositivos con IMEI o serie deben transferirse completos."
                    )
        return self


class InventoryReceivingRequest(BaseModel):
    store_id: int = Field(..., ge=1)
    note: str = Field(..., min_length=5, max_length=255)
    responsible: str | None = Field(default=None, max_length=120)
    reference: str | None = Field(default=None, max_length=120)
    lines: list[InventoryReceivingLine] = Field(..., min_length=1)


class InventoryReceivingSummary(BaseModel):
    lines: int = Field(..., ge=0)
    total_quantity: int = Field(..., ge=0)


class InventoryReceivingProcessed(BaseModel):
    identifier: str
    device_id: int
    quantity: int
    movement: MovementResponse


class InventoryReceivingResult(BaseModel):
    store_id: int
    processed: list[InventoryReceivingProcessed]
    totals: InventoryReceivingSummary
    auto_transfers: list[TransferOrderResponse] | None = None


class InventoryCountLine(BaseModel):
    device_id: int | None = Field(default=None, ge=1)
    imei: str | None = Field(default=None, min_length=3, max_length=64)
    serial: str | None = Field(default=None, min_length=3, max_length=64)
    counted: int = Field(..., ge=0)
    comment: str | None = Field(default=None, min_length=5, max_length=255)

    @model_validator(mode="after")
    def _ensure_identifier(self) -> "InventoryCountLine":
        if self.device_id is None and not (self.imei or self.serial):
            raise ValueError(
                "Cada línea debe incluir `device_id`, `imei` o `serial`."
            )
        return self


class InventoryCycleCountRequest(BaseModel):
    store_id: int = Field(..., ge=1)
    note: str = Field(..., min_length=5, max_length=255)
    responsible: str | None = Field(default=None, max_length=120)
    reference: str | None = Field(default=None, max_length=120)
    lines: list[InventoryCountLine] = Field(..., min_length=1)


class InventoryCountDiscrepancy(BaseModel):
    device_id: int
    sku: str | None = None
    expected: int
    counted: int
    delta: int
    movement: MovementResponse | None = None
    identifier: str | None = None


class InventoryCycleCountSummary(BaseModel):
    lines: int = Field(..., ge=0)
    adjusted: int = Field(..., ge=0)
    matched: int = Field(..., ge=0)
    total_variance: int = Field(...)


class InventoryCycleCountResult(BaseModel):
    store_id: int
    adjustments: list[InventoryCountDiscrepancy]
    totals: InventoryCycleCountSummary


class InventoryReservationRenew(BaseModel):
    expires_at: datetime


class InventoryReservationResponse(BaseModel):
    id: int
    store_id: int
    device_id: int
    status: InventoryState
    initial_quantity: int
    quantity: int
    reason: str
    resolution_reason: str | None
    reference_type: str | None
    reference_id: str | None
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    reserved_by_id: int | None = None
    resolved_by_id: int | None = None
    resolved_at: datetime | None = None
    consumed_at: datetime | None = None
    device: DeviceResponse | None = None

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


class InventoryAvailabilityStore(BaseModel):
    store_id: int
    store_name: str
    quantity: int


class InventoryAvailabilityRecord(BaseModel):
    reference: str
    sku: str | None = None
    product_name: str
    device_ids: list[int]
    total_quantity: int
    stores: list[InventoryAvailabilityStore]


class InventoryAvailabilityResponse(BaseModel):
    generated_at: datetime
    items: list[InventoryAvailabilityRecord]

    model_config = ConfigDict(from_attributes=True)
