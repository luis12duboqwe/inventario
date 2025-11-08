"""Servicios de listas de precios y resolución de tarifas personalizadas."""
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from .. import crud, schemas


_QUANTIZER = Decimal("0.01")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_QUANTIZER, rounding=ROUND_HALF_UP)


def _resolve_scope(
    price_list: "crud.models.PriceList",
    store_id: int | None,
    customer_id: int | None,
) -> str:
    if (
        store_id is not None
        and customer_id is not None
        and price_list.store_id == store_id
        and price_list.customer_id == customer_id
    ):
        return "store_customer"
    if (
        customer_id is not None
        and price_list.customer_id == customer_id
        and price_list.store_id is None
    ):
        return "customer"
    if (
        store_id is not None
        and price_list.store_id == store_id
        and price_list.customer_id is None
    ):
        return "store"
    return "global"


def list_price_lists(
    db: Session,
    *,
    store_id: int | None = None,
    customer_id: int | None = None,
    is_active: bool | None = None,
    include_items: bool = False,
) -> list[schemas.PriceListResponse]:
    price_lists = crud.list_price_lists(
        db,
        store_id=store_id,
        customer_id=customer_id,
        is_active=is_active,
        include_items=include_items,
    )
    return [
        schemas.PriceListResponse.model_validate(
            price_list, from_attributes=True
        )
        for price_list in price_lists
    ]


def get_price_list(
    db: Session,
    price_list_id: int,
    *,
    include_items: bool = True,
) -> schemas.PriceListResponse:
    price_list = crud.get_price_list(
        db, price_list_id, include_items=include_items
    )
    return schemas.PriceListResponse.model_validate(
        price_list, from_attributes=True
    )


def create_price_list(
    db: Session,
    payload: schemas.PriceListCreate,
    *,
    performed_by_id: int | None = None,
    include_items: bool = True,
) -> schemas.PriceListResponse:
    price_list = crud.create_price_list(
        db, payload, performed_by_id=performed_by_id
    )
    if include_items:
        price_list = crud.get_price_list(
            db, price_list.id, include_items=True
        )
    return schemas.PriceListResponse.model_validate(
        price_list, from_attributes=True
    )


def update_price_list(
    db: Session,
    price_list_id: int,
    payload: schemas.PriceListUpdate,
    *,
    performed_by_id: int | None = None,
    include_items: bool = True,
) -> schemas.PriceListResponse:
    price_list = crud.update_price_list(
        db,
        price_list_id,
        payload,
        performed_by_id=performed_by_id,
    )
    if include_items:
        price_list = crud.get_price_list(
            db, price_list.id, include_items=True
        )
    return schemas.PriceListResponse.model_validate(
        price_list, from_attributes=True
    )


def delete_price_list(
    db: Session,
    price_list_id: int,
    *,
    performed_by_id: int | None = None,
) -> None:
    crud.delete_price_list(
        db, price_list_id, performed_by_id=performed_by_id
    )


def get_price_list_item(
    db: Session,
    item_id: int,
) -> schemas.PriceListItemResponse:
    item = crud.get_price_list_item(db, item_id)
    return schemas.PriceListItemResponse.model_validate(
        item, from_attributes=True
    )


def create_price_list_item(
    db: Session,
    price_list_id: int,
    payload: schemas.PriceListItemCreate,
    *,
    performed_by_id: int | None = None,
) -> schemas.PriceListItemResponse:
    item = crud.create_price_list_item(
        db,
        price_list_id,
        payload,
        performed_by_id=performed_by_id,
    )
    return schemas.PriceListItemResponse.model_validate(
        item, from_attributes=True
    )


def update_price_list_item(
    db: Session,
    item_id: int,
    payload: schemas.PriceListItemUpdate,
    *,
    performed_by_id: int | None = None,
) -> schemas.PriceListItemResponse:
    item = crud.update_price_list_item(
        db,
        item_id,
        payload,
        performed_by_id=performed_by_id,
    )
    return schemas.PriceListItemResponse.model_validate(
        item, from_attributes=True
    )


def delete_price_list_item(
    db: Session,
    item_id: int,
    *,
    performed_by_id: int | None = None,
) -> None:
    crud.delete_price_list_item(
        db, item_id, performed_by_id=performed_by_id
    )


def resolve_device_price(
    db: Session,
    *,
    device_id: int,
    store_id: int | None = None,
    customer_id: int | None = None,
    reference_date: date | None = None,
    default_price: Decimal | None = None,
    default_currency: str = "MXN",
) -> schemas.PriceResolution | None:
    resolution = crud.resolve_price_for_device(
        db,
        device_id=device_id,
        store_id=store_id,
        customer_id=customer_id,
        reference_date=reference_date,
    )

    if resolution is None:
        if default_price is None:
            return None
        normalized_price = _quantize(default_price)
        currency = (default_currency or "MXN").strip().upper() or "MXN"
        return schemas.PriceResolution(
            device_id=device_id,
            price_list_id=None,
            price_list_name=None,
            scope="fallback",
            source="fallback",
            currency=currency,
            base_price=normalized_price,
            discount_percentage=None,
            final_price=normalized_price,
            valid_from=None,
            valid_until=None,
        )

    price_list, item = resolution
    base_price = _quantize(item.price)
    discount = (
        _quantize(item.discount_percentage)
        if item.discount_percentage is not None
        else None
    )
    final_price = base_price
    if discount is not None:
        final_price = _quantize(
            base_price * (Decimal("1") - (discount / Decimal("100")))
        )

    scope = _resolve_scope(price_list, store_id, customer_id)
    return schemas.PriceResolution(
        device_id=device_id,
        price_list_id=price_list.id,
        price_list_name=price_list.name,
        scope=scope,
        source="price_list",
        currency=price_list.currency,
        base_price=base_price,
        discount_percentage=discount,
        final_price=final_price,
        valid_from=price_list.valid_from,
        valid_until=price_list.valid_until,
    )


__all__ = [
    "list_price_lists",
    "get_price_list",
    "create_price_list",
    "update_price_list",
    "delete_price_list",
    "get_price_list_item",
    "create_price_list_item",
    "update_price_list_item",
    "delete_price_list_item",
    "resolve_device_price",
]
