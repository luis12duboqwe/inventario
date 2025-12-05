"""Esquemas para la gestión de proveedores."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from .common import ContactHistoryEntry, normalize_optional_rtn_value


class SupplierContact(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    position: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=255)

    @field_validator("name", "position", "email", "phone", "notes", mode="before")
    @classmethod
    def _normalize_contact_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class SupplierBase(BaseModel):
    rtn: str | None = Field(default=None, max_length=30)
    payment_terms: str | None = Field(default=None, max_length=80)
    contact_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=500)
    outstanding_debt: Decimal = Field(default=Decimal("0"))
    history: list[ContactHistoryEntry] = Field(default_factory=list)
    contact_info: list[SupplierContact] = Field(default_factory=list)
    products_supplied: list[str] = Field(default_factory=list)

    @field_validator(
        "rtn",
        "payment_terms",
        "contact_name",
        "email",
        "phone",
        "address",
        "notes",
        mode="before",
    )
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("rtn", mode="before")
    @classmethod
    def _normalize_rtn(cls, value: str | None) -> str | None:
        return normalize_optional_rtn_value(value)

    @field_validator("products_supplied", mode="before")
    @classmethod
    def _normalize_products(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (str, bytes)):
            candidates = [value]
        else:
            candidates = list(value) if isinstance(
                value, Iterable) else [value]
        normalized: list[str] = []
        for candidate in candidates:
            if candidate is None:
                continue
            text = str(candidate).strip()
            if not text:
                continue
            if text not in normalized:
                normalized.append(text)
        return normalized

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
    rtn: str | None = Field(default=None, max_length=30)
    payment_terms: str | None = Field(default=None, max_length=80)
    contact_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=500)
    outstanding_debt: Decimal | None = Field(default=None)
    history: list[ContactHistoryEntry] | None = Field(default=None)
    contact_info: list[SupplierContact] | None = Field(default=None)
    products_supplied: list[str] | None = Field(default=None)

    @field_validator(
        "name",
        "rtn",
        "payment_terms",
        "contact_name",
        "email",
        "phone",
        "address",
        "notes",
        mode="before",
    )
    @classmethod
    def _normalize_update_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("rtn", mode="before")
    @classmethod
    def _normalize_update_rtn(cls, value: str | None) -> str | None:
        return normalize_optional_rtn_value(value)

    @field_validator("products_supplied", mode="before")
    @classmethod
    def _normalize_products_update(cls, value: object) -> list[str] | None:
        if value is None:
            return None
        if isinstance(value, (str, bytes)):
            candidates = [value]
        else:
            candidates = list(value) if isinstance(
                value, Iterable) else [value]
        normalized: list[str] = []
        for candidate in candidates:
            if candidate is None:
                continue
            text = str(candidate).strip()
            if not text:
                continue
            if text not in normalized:
                normalized.append(text)
        return normalized


class SupplierResponse(SupplierBase):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = Field(default=False)
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SupplierAccountsPayableBucket(BaseModel):
    label: str
    days_from: int
    days_to: int | None
    amount: float
    percentage: float
    count: int


class SupplierAccountsPayableSupplier(BaseModel):
    supplier_id: int
    supplier_name: str
    rtn: str | None
    payment_terms: str | None
    outstanding_debt: float
    bucket_label: str
    bucket_from: int
    bucket_to: int | None
    days_outstanding: int
    last_activity: datetime | None
    contact_name: str | None
    contact_email: str | None
    contact_phone: str | None
    products_supplied: list[str]
    contact_info: list[SupplierContact] = Field(default_factory=list)


class SupplierAccountsPayableSummary(BaseModel):
    total_balance: float
    total_overdue: float
    supplier_count: int
    generated_at: datetime
    buckets: list[SupplierAccountsPayableBucket]


class SupplierAccountsPayableResponse(BaseModel):
    summary: SupplierAccountsPayableSummary
    suppliers: list[SupplierAccountsPayableSupplier]


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
    """Datos requeridos para registrar un nuevo lote de proveedor."""


class SupplierBatchUpdate(BaseModel):
    model_name: str | None = Field(default=None, max_length=120)
    batch_code: str | None = Field(default=None, max_length=80)
    unit_cost: Decimal | None = Field(default=None, ge=Decimal("0"))
    quantity: int | None = Field(default=None, ge=0)
    purchase_date: date | None = None
    notes: str | None = Field(default=None, max_length=255)
    store_id: int | None = Field(default=None, ge=1)
    device_id: int | None = Field(default=None, ge=1)

    model_config = ConfigDict(protected_namespaces=())

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

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class SupplierBatchOverviewItem(BaseModel):
    supplier_id: int
    supplier_name: str
    batch_count: int = Field(ge=0)
    total_quantity: int = Field(ge=0)
    total_value: float = Field(ge=0)
    latest_purchase_date: date
    latest_batch_code: str | None = None
    latest_unit_cost: float | None = Field(default=None, ge=0)
