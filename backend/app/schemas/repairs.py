from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_serializer,
    field_validator,
    model_validator,
)

from ..models import RepairPartSource, RepairStatus


class RepairOrderPartPayload(BaseModel):
    device_id: int | None = Field(default=None, ge=1)
    part_name: str | None = Field(default=None, max_length=120)
    source: RepairPartSource = Field(
        default=RepairPartSource.STOCK)  # // [PACK37-backend]
    quantity: int = Field(..., ge=1)
    unit_cost: Decimal | None = Field(default=None, ge=Decimal("0"))

    @field_validator("unit_cost")
    @classmethod
    def _normalize_unit_cost(cls, value: Decimal | None) -> Decimal:
        if value is None:
            return Decimal("0")
        return value

    @field_validator("part_name")
    @classmethod
    def _normalize_part_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class RepairOrderCreate(BaseModel):
    store_id: int = Field(..., ge=1)
    customer_id: int | None = Field(default=None, ge=1)
    customer_name: str | None = Field(default=None, max_length=120)
    customer_contact: str | None = Field(
        default=None, max_length=120)  # // [PACK37-backend]
    technician_name: str = Field(..., max_length=120)
    damage_type: str = Field(..., max_length=120)
    diagnosis: str | None = Field(
        default=None, max_length=500)  # // [PACK37-backend]
    device_model: str | None = Field(
        default=None, max_length=120)  # // [PACK37-backend]
    imei: str | None = Field(
        default=None, max_length=40)  # // [PACK37-backend]
    device_description: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=500)
    labor_cost: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    parts: list[RepairOrderPartPayload] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_repair_create_aliases(cls, data: Any) -> Any:  # pragma: no cover
        if isinstance(data, dict) and "damage_type" not in data:
            for k in ("issue",):
                if k in data:
                    data["damage_type"] = data[k]
                    break
        return data

    @field_validator(
        "customer_name",
        "customer_contact",
        "technician_name",
        "damage_type",
        "diagnosis",
        "device_model",
        "imei",
        "device_description",
        "notes",
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
    customer_contact: str | None = Field(
        default=None, max_length=120)  # // [PACK37-backend]
    technician_name: str | None = Field(default=None, max_length=120)
    damage_type: str | None = Field(default=None, max_length=120)
    diagnosis: str | None = Field(
        default=None, max_length=500)  # // [PACK37-backend]
    device_model: str | None = Field(
        default=None, max_length=120)  # // [PACK37-backend]
    imei: str | None = Field(
        default=None, max_length=40)  # // [PACK37-backend]
    device_description: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=500)
    status: RepairStatus | None = None
    labor_cost: Decimal | None = Field(default=None, ge=Decimal("0"))
    parts: list[RepairOrderPartPayload] | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_repair_update_aliases(cls, data: Any) -> Any:  # pragma: no cover
        if isinstance(data, dict) and "damage_type" not in data:
            for k in ("issue",):
                if k in data:
                    data["damage_type"] = data[k]
                    break
        return data

    @field_validator(
        "customer_name",
        "customer_contact",
        "technician_name",
        "damage_type",
        "diagnosis",
        "device_model",
        "imei",
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


class RepairOrderPartsRequest(BaseModel):  # // [PACK37-backend]
    parts: list[RepairOrderPartPayload] = Field(default_factory=list)


class RepairOrderCloseRequest(BaseModel):  # // [PACK37-backend]
    labor_cost: Decimal | None = Field(default=None, ge=Decimal("0"))
    parts: list[RepairOrderPartPayload] | None = None


class RepairOrderPartResponse(BaseModel):
    id: int
    repair_order_id: int
    device_id: int | None
    part_name: str | None = None  # // [PACK37-backend]
    source: RepairPartSource = Field(
        default=RepairPartSource.STOCK)  # // [PACK37-backend]
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
    customer_contact: str | None = None  # // [PACK37-backend]
    technician_name: str
    damage_type: str
    diagnosis: str | None = None  # // [PACK37-backend]
    device_model: str | None = None  # // [PACK37-backend]
    imei: str | None = None  # // [PACK37-backend]
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
            RepairStatus.CANCELADO: "🔴",  # // [PACK37-backend]
        }
        return mapping.get(self.status, "⬜")

    @field_serializer("labor_cost", "parts_cost", "total_cost")
    @classmethod
    def _serialize_cost(cls, value: Decimal) -> float:
        return float(value)
