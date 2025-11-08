"""Servicios para resolver precios corporativos basados en listas dedicadas."""
from __future__ import annotations

from datetime import datetime
from datetime import datetime
from decimal import Decimal
from typing import Iterable

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..models import Device, PriceList, PriceListItem


def _utc_now() -> datetime:
    return datetime.utcnow()


def _scope_rank(price_list: PriceList) -> int:
    if price_list.store_id is not None and price_list.customer_id is not None:
        return 0
    if price_list.customer_id is not None:
        return 1
    if price_list.store_id is not None:
        return 2
    return 3


def list_applicable_price_lists(
    db: Session,
    *,
    store_id: int | None = None,
    customer_id: int | None = None,
    include_inactive: bool = False,
) -> list[PriceList]:
    """Obtiene las listas activas compatibles con la combinación solicitada."""

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
    """Determina el mejor precio disponible para un dispositivo concreto."""

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
    """Devuelve el mejor precio para cada dispositivo indicado."""

    mapping: dict[int, tuple[PriceList, PriceListItem]] = {}
    for device in devices:
        resolved = resolve_price_for_device(
            db, device, store_id=store_id, customer_id=customer_id
        )
        if resolved:
            mapping[device.id] = resolved
    return mapping


def compute_effective_price(
    db: Session,
    device: Device,
    *,
    store_id: int | None = None,
    customer_id: int | None = None,
) -> Decimal:
    """Entrega el precio final considerando listas priorizadas; fallback al unitario."""

    resolved = resolve_price_for_device(
        db, device, store_id=store_id, customer_id=customer_id
    )
    if resolved:
        _, item = resolved
        return item.price
    return device.unit_price
