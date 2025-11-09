"""Servicios de negocio relacionados con listas de precios y resolución de tarifas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..models import Device, PriceList, PriceListItem

_QUANTIZER = Decimal("0.01")


def _quantize(value: Decimal) -> Decimal:
    """Normaliza los valores monetarios a dos decimales con redondeo corporativo."""

    return value.quantize(_QUANTIZER, rounding=ROUND_HALF_UP)


def _utc_now() -> datetime:
    """Retorna la marca de tiempo actual en UTC."""

    return datetime.utcnow()


def _scope_rank(price_list: PriceList) -> int:
    """Determina la prioridad de alcance de una lista de precios."""

    if price_list.store_id is not None and price_list.customer_id is not None:
        return 0
    if price_list.customer_id is not None:
        return 1
    if price_list.store_id is not None:
        return 2
    return 3


def _resolve_scope(
    price_list: PriceList,
    store_id: int | None,
    customer_id: int | None,
) -> str:
    """Calcula el alcance efectivo de la lista según la combinación solicitada."""

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
    include_inactive: bool = True,
    include_global: bool = True,
    include_items: bool = True,
) -> list[schemas.PriceListResponse]:
    """Lista las configuraciones de precios disponibles según los filtros.

    Los resultados se devuelven como modelos Pydantic listos para exposición en la API.
    """

    price_lists = crud.list_price_lists(
        db,
        store_id=store_id,
        customer_id=customer_id,
        include_inactive=include_inactive,
        include_global=include_global,
    )
    responses = [
        schemas.PriceListResponse.model_validate(price_list, from_attributes=True)
        for price_list in price_lists
    ]
    if not include_items:
        for response in responses:
            response.items = []
    return responses


def get_price_list(
    db: Session,
    price_list_id: int,
    *,
    include_items: bool = True,
) -> schemas.PriceListResponse:
    """Obtiene el detalle de una lista de precios específica."""

    price_list = crud.get_price_list(db, price_list_id)
    response = schemas.PriceListResponse.model_validate(
        price_list, from_attributes=True
    )
    if not include_items:
        response.items = []
    return response


def create_price_list(
    db: Session,
    payload: schemas.PriceListCreate,
    *,
    performed_by_id: int | None = None,
    include_items: bool = True,
) -> schemas.PriceListResponse:
    """Registra una nueva lista de precios y devuelve su representación serializada."""

    price_list = crud.create_price_list(
        db, payload, performed_by_id=performed_by_id
    )
    if include_items:
        price_list = crud.get_price_list(db, price_list.id)
    response = schemas.PriceListResponse.model_validate(
        price_list, from_attributes=True
    )
    if not include_items:
        response.items = []
    return response


def update_price_list(
    db: Session,
    price_list_id: int,
    payload: schemas.PriceListUpdate,
    *,
    performed_by_id: int | None = None,
    include_items: bool = True,
) -> schemas.PriceListResponse:
    """Actualiza una lista de precios y retorna el resultado normalizado."""

    price_list = crud.update_price_list(
        db,
        price_list_id,
        payload,
        performed_by_id=performed_by_id,
    )
    if include_items:
        price_list = crud.get_price_list(db, price_list.id)
    response = schemas.PriceListResponse.model_validate(
        price_list, from_attributes=True
    )
    if not include_items:
        response.items = []
    return response


def delete_price_list(
    db: Session,
    price_list_id: int,
    *,
    performed_by_id: int | None = None,
) -> None:
    """Elimina una lista de precios existente."""

    crud.delete_price_list(db, price_list_id, performed_by_id=performed_by_id)


def get_price_list_item(
    db: Session,
    item_id: int,
) -> schemas.PriceListItemResponse:
    """Obtiene un elemento concreto de una lista de precios."""

    item = crud.get_price_list_item(db, item_id)
    return schemas.PriceListItemResponse.model_validate(item, from_attributes=True)


def create_price_list_item(
    db: Session,
    price_list_id: int,
    payload: schemas.PriceListItemCreate,
    *,
    performed_by_id: int | None = None,
) -> schemas.PriceListItemResponse:
    """Registra un nuevo precio dentro de una lista."""

    item = crud.create_price_list_item(
        db,
        price_list_id,
        payload,
        performed_by_id=performed_by_id,
    )
    return schemas.PriceListItemResponse.model_validate(item, from_attributes=True)


def update_price_list_item(
    db: Session,
    item_id: int,
    payload: schemas.PriceListItemUpdate,
    *,
    performed_by_id: int | None = None,
) -> schemas.PriceListItemResponse:
    """Actualiza un elemento de lista y devuelve la versión consolidada."""

    item = crud.update_price_list_item(
        db,
        item_id,
        payload,
        performed_by_id=performed_by_id,
    )
    return schemas.PriceListItemResponse.model_validate(item, from_attributes=True)


def delete_price_list_item(
    db: Session,
    item_id: int,
    *,
    performed_by_id: int | None = None,
) -> None:
    """Elimina un precio asociado a una lista."""

    crud.delete_price_list_item(db, item_id, performed_by_id=performed_by_id)


def list_applicable_price_lists(
    db: Session,
    *,
    store_id: int | None = None,
    customer_id: int | None = None,
    include_inactive: bool = False,
) -> list[PriceList]:
    """Obtiene las listas aplicables considerando vigencias y alcance."""

    now = _utc_now()
    statement = select(PriceList).order_by(PriceList.priority.asc(), PriceList.id.asc())

    if not include_inactive:
        statement = statement.where(PriceList.is_active.is_(True))

    statement = statement.where(
        or_(PriceList.starts_at.is_(None), PriceList.starts_at <= now),
        or_(PriceList.ends_at.is_(None), PriceList.ends_at >= now),
    )

    if store_id is None:
        statement = statement.where(PriceList.store_id.is_(None))
    else:
        statement = statement.where(
            or_(PriceList.store_id == store_id, PriceList.store_id.is_(None))
        )

    if customer_id is None:
        statement = statement.where(PriceList.customer_id.is_(None))
    else:
        statement = statement.where(
            or_(PriceList.customer_id == customer_id, PriceList.customer_id.is_(None))
        )

    return list(db.scalars(statement))


def resolve_price_for_device(
    db: Session,
    device: Device,
    *,
    store_id: int | None = None,
    customer_id: int | None = None,
) -> tuple[PriceList, PriceListItem] | None:
    """Encuentra la mejor lista de precios para el dispositivo indicado."""

    price_lists = list_applicable_price_lists(
        db,
        store_id=store_id,
        customer_id=customer_id,
        include_inactive=False,
    )
    if not price_lists:
        return None

    statement = (
        select(PriceListItem)
        .where(PriceListItem.price_list_id.in_([pl.id for pl in price_lists]))
        .where(PriceListItem.device_id == device.id)
    )
    items = {item.price_list_id: item for item in db.scalars(statement)}

    for price_list in sorted(
        price_lists, key=lambda pl: (_scope_rank(pl), pl.priority, pl.id)
    ):
        item = items.get(price_list.id)
        if item is not None:
            return price_list, item
    return None


def resolve_prices_for_devices(
    db: Session,
    devices: Iterable[Device],
    *,
    store_id: int | None = None,
    customer_id: int | None = None,
) -> dict[int, tuple[PriceList, PriceListItem]]:
    """Determina precios aplicables para un conjunto de dispositivos."""

    mapping: dict[int, tuple[PriceList, PriceListItem]] = {}
    for device in devices:
        resolved = resolve_price_for_device(
            db, device, store_id=store_id, customer_id=customer_id
        )
        if resolved:
            mapping[device.id] = resolved
    return mapping


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
    """Obtiene la resolución de precio para el dispositivo solicitado."""

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


def compute_effective_price(
    db: Session,
    device: Device,
    *,
    store_id: int | None = None,
    customer_id: int | None = None,
) -> Decimal:
    """Entrega el precio efectivo de un dispositivo considerando listas aplicables."""

    resolved = resolve_price_for_device(
        db, device, store_id=store_id, customer_id=customer_id
    )
    if resolved:
        _, item = resolved
        return item.price
    return device.unit_price


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
    "list_applicable_price_lists",
    "resolve_price_for_device",
    "resolve_prices_for_devices",
    "resolve_device_price",
    "compute_effective_price",
]
