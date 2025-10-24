"""Esquemas Pydantic para el módulo POS comercial del wrapper."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Iterable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from backend.models.pos import PaymentMethod, SaleStatus


class SaleItemCreate(BaseModel):
    """Carga útil para registrar productos en una venta abierta."""

    description: str = Field(..., min_length=1, max_length=255)
    quantity: int = Field(..., ge=1)
    unit_price: Decimal = Field(..., gt=Decimal("0"))
    discount_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    tax_rate: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    product_id: int | None = Field(default=None, ge=1)

    @field_validator("description")
    @classmethod
    def _normalize_description(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("La descripción del artículo es obligatoria.")
        return normalized

    @field_validator("discount_amount")
    @classmethod
    def _normalize_discount(cls, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"))

    @field_validator("tax_rate")
    @classmethod
    def _normalize_tax_rate(cls, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"))

    @field_validator("unit_price")
    @classmethod
    def _normalize_unit_price(cls, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"))


class SaleItemsRequest(BaseModel):
    """Petición para añadir múltiples artículos a una venta."""

    items: list[SaleItemCreate] = Field(..., min_length=1)


class SaleCreate(BaseModel):
    """Solicitud para iniciar una venta POS."""

    store_id: int = Field(..., ge=1)
    notes: str | None = Field(default=None, max_length=255)


class PaymentCreate(BaseModel):
    """Carga útil para registrar pagos durante el checkout."""

    method: PaymentMethod
    amount: Decimal = Field(..., gt=Decimal("0"))
    reference: str | None = Field(default=None, max_length=120)

    @field_validator("amount")
    @classmethod
    def _normalize_amount(cls, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"))

    @field_validator("reference")
    @classmethod
    def _normalize_reference(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CheckoutRequest(BaseModel):
    """Petición para cerrar una venta con pagos múltiples."""

    payments: list[PaymentCreate] = Field(..., min_length=1)


class SaleActionRequest(BaseModel):
    """Cuerpo genérico para acciones de hold/resume/void."""

    reason: str | None = Field(default=None, max_length=255)


class SaleItemResponse(BaseModel):
    """Detalle de artículo expuesto en la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int | None
    description: str
    quantity: int
    unit_price: Decimal
    discount_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    line_subtotal: Decimal
    total_amount: Decimal

    @field_serializer("unit_price", "discount_amount", "tax_amount", "line_subtotal", "total_amount")
    def _serialize_decimal(self, value: Decimal) -> float:
        return float(value)

    @field_serializer("tax_rate")
    def _serialize_tax_rate(self, value: Decimal) -> float:
        return float(value)


class PaymentResponse(BaseModel):
    """Representación pública de un pago registrado."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    method: PaymentMethod
    amount: Decimal
    reference: str | None
    created_at: datetime

    @field_serializer("amount")
    def _serialize_amount(self, value: Decimal) -> float:
        return float(value)


class SaleResponse(BaseModel):
    """Respuesta base para operaciones del POS comercial."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    status: SaleStatus
    notes: str | None
    subtotal_amount: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime
    held_at: datetime | None
    completed_at: datetime | None
    voided_at: datetime | None
    items: list[SaleItemResponse]
    payments: list[PaymentResponse]

    @field_serializer(
        "subtotal_amount",
        "discount_total",
        "tax_total",
        "total_amount",
    )
    def _serialize_decimal(self, value: Decimal) -> float:
        return float(value)


class CheckoutResponse(SaleResponse):
    """Respuesta utilizada tras finalizar una venta."""

    request_id: UUID | None = None


class ReceiptResponse(SaleResponse):
    """Detalle de recibo accesible vía GET /pos/receipt/{id}."""

    def total_paid(self) -> float:
        return float(sum((payment.amount for payment in self.payments), Decimal("0")))


def build_sale_response(model: SaleResponse | None, *, request_id: UUID | None = None) -> CheckoutResponse | SaleResponse:
    """Helper para ajustar la respuesta incluyendo el identificador de solicitud."""

    if isinstance(model, CheckoutResponse):
        model.request_id = request_id
        return model
    response = CheckoutResponse(**model.model_dump(), request_id=request_id)
    return response


def compute_decimal_sum(values: Iterable[Decimal]) -> Decimal:
    """Utilidad para sumar decimales asegurando dos decimales."""

    return sum(values, Decimal("0")).quantize(Decimal("0.01"))
