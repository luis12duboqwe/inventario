from __future__ import annotations
from decimal import Decimal
from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
)


class ProductVariantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    variant_sku: str = Field(..., min_length=1, max_length=80)
    barcode: str | None = Field(default=None, max_length=120)
    unit_price_override: Decimal | None = Field(default=None, ge=Decimal("0"))
    is_default: bool = Field(default=False)
    is_active: bool = Field(default=True)

    @field_serializer("unit_price_override")
    @classmethod
    def _serialize_price(cls, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)


class ProductVariantCreate(ProductVariantBase):
    pass


class ProductVariantUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    variant_sku: str | None = Field(default=None, max_length=80)
    barcode: str | None = Field(default=None, max_length=120)
    unit_price_override: Decimal | None = Field(default=None, ge=Decimal("0"))
    is_default: bool | None = Field(default=None)
    is_active: bool | None = Field(default=None)

    @field_serializer("unit_price_override")
    @classmethod
    def _serialize_update_price(cls, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)


class ProductVariantResponse(ProductVariantBase):
    id: int
    device_id: int
    store_id: int
    device_sku: str
    device_name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductBundleItemBase(BaseModel):
    device_id: int = Field(..., ge=1)
    variant_id: int | None = Field(default=None, ge=1)
    quantity: int = Field(default=1, ge=1)


class ProductBundleItemCreate(ProductBundleItemBase):
    pass


class ProductBundleItemResponse(ProductBundleItemBase):
    id: int
    variant_name: str | None = Field(default=None)
    device_sku: str
    device_name: str

    model_config = ConfigDict(from_attributes=True)


class ProductBundleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    bundle_sku: str = Field(..., min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    base_price: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    is_active: bool = Field(default=True)

    @field_serializer("base_price")
    @classmethod
    def _serialize_base_price(cls, value: Decimal) -> float:
        return float(value)


class ProductBundleCreate(ProductBundleBase):
    store_id: int | None = Field(default=None, ge=1)
    items: list[ProductBundleItemCreate] = Field(default_factory=list)


class ProductBundleUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    bundle_sku: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    base_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    is_active: bool | None = Field(default=None)
    store_id: int | None = Field(default=None, ge=1)
    items: list[ProductBundleItemCreate] | None = Field(default=None)

    @field_serializer("base_price")
    @classmethod
    def _serialize_update_price(cls, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)


class ProductBundleResponse(ProductBundleBase):
    id: int
    store_id: int | None
    created_at: datetime
    updated_at: datetime
    items: list[ProductBundleItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
