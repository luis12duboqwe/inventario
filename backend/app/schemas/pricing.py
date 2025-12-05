from __future__ import annotations
from decimal import Decimal
from datetime import date, datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
    field_serializer,
)


class PriceListBase(BaseModel):
    """Información común de una lista de precios corporativa."""

    name: str = Field(
        ...,
        min_length=3,
        max_length=120,
        description="Nombre visible para identificar la lista de precios.",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Descripción opcional del alcance o uso de la lista.",
    )
    priority: int = Field(
        default=100,
        ge=0,
        le=10000,
        description="Prioridad corporativa (0 = máxima prioridad).",
    )
    is_active: bool = Field(
        default=True,
        description="Indica si la lista está habilitada para resolver precios.",
    )
    store_id: int | None = Field(
        default=None,
        ge=1,
        description="Sucursal asociada cuando la lista es específica para una tienda.",
    )
    customer_id: int | None = Field(
        default=None,
        ge=1,
        description="Cliente corporativo preferente ligado a la lista.",
    )
    currency: str = Field(
        default="MXN",
        min_length=3,
        max_length=10,
        description="Moneda ISO 4217 en la que se expresan los precios.",
    )
    valid_from: date | None = Field(
        default=None,
        description="Fecha a partir de la cual la lista entra en vigor.",
    )
    valid_until: date | None = Field(
        default=None,
        description="Fecha límite de vigencia de la lista de precios.",
    )
    starts_at: datetime | None = Field(
        default=None,
        description="Fecha de inicio de vigencia en hora exacta (UTC).",
    )
    ends_at: datetime | None = Field(
        default=None,
        description="Fecha de término de vigencia en hora exacta (UTC).",
    )

    @field_validator("name", mode="before")
    @classmethod
    def _normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("El nombre debe tener al menos 3 caracteres.")
        return normalized

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("currency", mode="before")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) < 3:
            raise ValueError("La moneda debe tener al menos 3 caracteres.")
        return normalized

    @model_validator(mode="after")
    def _validate_dates(self) -> "PriceListBase":
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_from > self.valid_until
        ):
            raise ValueError(
                "La fecha de inicio no puede ser posterior a la fecha de fin."
            )
        if (
            self.starts_at is not None
            and self.ends_at is not None
            and self.ends_at <= self.starts_at
        ):
            raise ValueError(
                "La fecha de término debe ser posterior al inicio.")
        return self


class PriceListCreate(PriceListBase):
    """Carga útil para registrar una nueva lista de precios."""


class PriceListUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    priority: int | None = Field(default=None, ge=0, le=10000)
    is_active: bool | None = Field(default=None)
    store_id: int | None = Field(default=None, ge=1)
    customer_id: int | None = Field(default=None, ge=1)
    starts_at: datetime | None = Field(default=None)
    ends_at: datetime | None = Field(default=None)
    valid_from: date | None = Field(default=None)
    valid_until: date | None = Field(default=None)

    @model_validator(mode="after")
    def _validate_dates(self) -> "PriceListUpdate":
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_from > self.valid_until
        ):
            raise ValueError(
                "La fecha de inicio no puede ser posterior a la fecha de fin."
            )
        if (
            self.starts_at is not None
            and self.ends_at is not None
            and self.ends_at <= self.starts_at
        ):
            raise ValueError(
                "La fecha de término debe ser posterior al inicio.")
        return self


class PriceListItemBase(BaseModel):
    """Definición de un precio para un producto dentro de una lista."""

    device_id: int = Field(
        ...,
        ge=1,
        description="Identificador del dispositivo dentro del catálogo corporativo.",
    )
    price: Decimal = Field(
        ...,
        gt=Decimal("0"),
        description="Precio específico definido en la lista.",
    )
    discount_percentage: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("100"),
        description="Descuento porcentual adicional aplicado al precio base.",
    )
    currency: str = Field(
        default="MXN",
        min_length=3,
        max_length=8,
        description="Moneda ISO 4217 asociada al precio.",
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Notas internas sobre la regla de precios.",
    )

    @field_validator("currency", mode="before")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) < 3:
            raise ValueError("La moneda debe contener al menos 3 caracteres.")
        return normalized

    @field_validator("notes", mode="before")
    @classmethod
    def _normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class PriceListItemCreate(PriceListItemBase):
    """Carga útil para agregar un producto a una lista de precios."""


class PriceListItemUpdate(BaseModel):
    """Campos disponibles para actualizar un precio de catálogo."""

    price: Decimal | None = Field(default=None, gt=Decimal("0"))
    currency: str | None = Field(default=None, min_length=3, max_length=8)
    discount_percentage: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("100"),
    )
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("currency", mode="before")
    @classmethod
    def _normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if len(normalized) < 3:
            raise ValueError("La moneda debe contener al menos 3 caracteres.")
        return normalized

    @field_validator("notes", mode="before")
    @classmethod
    def _normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def _ensure_valid_price(self) -> "PriceListItemUpdate":
        if self.price is not None and self.price <= Decimal("0"):
            raise ValueError("El precio debe ser mayor a cero.")
        return self


class PriceListItemResponse(PriceListItemBase):
    id: int
    price_list_id: int
    is_deleted: bool = Field(default=False)
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("price")
    @classmethod
    def _serialize_price(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("discount_percentage")
    @classmethod
    def _serialize_discount(cls, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)


class PriceListResponse(PriceListBase):
    id: int
    scope: str
    is_deleted: bool = Field(default=False)
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    items: list[PriceListItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class PriceResolution(BaseModel):
    """Resultado de resolver un precio con base en listas disponibles."""

    device_id: int = Field(..., ge=1)
    price_list_id: int | None = Field(default=None, ge=1)
    price_list_name: str | None = Field(default=None, max_length=120)
    base_price: Decimal = Field(..., ge=Decimal("0"))
    final_price: Decimal = Field(..., ge=Decimal("0"))
    discount_applied: Decimal = Field(default=Decimal("0"))
    currency: str = Field(default="MXN")
    applied_rule: str | None = None

    @field_serializer("base_price", "final_price", "discount_applied")
    @classmethod
    def _serialize_decimals(cls, value: Decimal) -> float:
        return float(value)


class PriceEvaluationRequest(BaseModel):
    device_id: int = Field(..., ge=1)
    store_id: int | None = Field(default=None, ge=1)
    customer_id: int | None = Field(default=None, ge=1)


class PriceEvaluationResponse(BaseModel):
    device_id: int
    price_list_id: int | None = None
    priority: int | None = None
    scope: str | None = None
    price: float | None = None
    currency: str | None = None
