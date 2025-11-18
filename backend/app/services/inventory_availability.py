"""Servicios agregados para consultar existencias por sucursal con cache ligero."""
from __future__ import annotations

import copy
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .. import models
from ..utils.cache import TTLCache

_CACHE_TTL_SECONDS = 30.0
_MAX_LIMIT = 250

_AvailabilityRecord = Mapping[str, Any]
_AvailabilityResponse = Mapping[str, Any]

_CACHE: TTLCache[_AvailabilityResponse] = TTLCache(_CACHE_TTL_SECONDS)


def _normalize_reference(sku: str | None, device_id: int) -> str:
    normalized = (sku or "").strip().lower()
    if normalized:
        return normalized
    return f"device:{device_id}"


def _sanitize_skus(skus: Sequence[str] | None) -> tuple[str, ...]:
    if not skus:
        return tuple()
    normalized = {sku.strip().lower() for sku in skus if sku and sku.strip()}
    return tuple(sorted(normalized))


def _sanitize_device_ids(device_ids: Sequence[int] | None) -> tuple[int, ...]:
    if not device_ids:
        return tuple()
    normalized = {int(device_id) for device_id in device_ids if int(device_id) > 0}
    return tuple(sorted(normalized))


def _build_cache_key(
    *,
    skus: tuple[str, ...],
    device_ids: tuple[int, ...],
    query: str | None,
    limit: int,
) -> tuple[str, tuple[int, ...], str, int]:
    normalized_query = (query or "").strip().lower()
    return ("|".join(skus), device_ids, normalized_query, limit)


def _merge_store_entry(
    stores: dict[int, dict[str, Any]],
    *,
    store_id: int,
    store_name: str,
    quantity: int,
) -> None:
    entry = stores.get(store_id)
    if entry is None:
        entry = {"store_id": store_id, "store_name": store_name, "quantity": 0}
        stores[store_id] = entry
    entry["quantity"] = int(entry.get("quantity", 0)) + int(quantity)


def get_inventory_availability(
    db: Session,
    *,
    skus: Sequence[str] | None = None,
    device_ids: Sequence[int] | None = None,
    search: str | None = None,
    limit: int = 50,
) -> _AvailabilityResponse:
    """Obtiene existencias agrupadas por SKU y sucursal con cache en memoria."""

    normalized_limit = max(1, min(limit, _MAX_LIMIT))
    normalized_skus = _sanitize_skus(skus)
    normalized_device_ids = _sanitize_device_ids(device_ids)
    cache_key = _build_cache_key(
        skus=normalized_skus,
        device_ids=normalized_device_ids,
        query=search,
        limit=normalized_limit,
    )
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return copy.deepcopy(cached)

    sku_column = func.coalesce(func.lower(models.Device.sku), "")
    stmt = (
        select(
            models.Device.id.label("device_id"),
            models.Device.sku.label("sku"),
            models.Device.name.label("name"),
            models.Device.quantity.label("quantity"),
            models.Store.id.label("store_id"),
            models.Store.name.label("store_name"),
        )
        .join(models.Store, models.Store.id == models.Device.store_id)
        .order_by(sku_column.asc(), models.Device.id.asc(), models.Store.name.asc())
    )

    if normalized_skus:
        stmt = stmt.where(sku_column.in_(normalized_skus))
    if normalized_device_ids:
        stmt = stmt.where(models.Device.id.in_(normalized_device_ids))

    normalized_query = (search or "").strip().lower()
    if normalized_query:
        pattern = f"%{normalized_query}%"
        stmt = stmt.where(
            or_(
                sku_column.like(pattern),
                func.lower(models.Device.name).like(pattern),
                func.lower(models.Device.modelo).like(pattern),
                func.lower(models.Device.marca).like(pattern),
                func.lower(models.Device.imei).like(pattern),
                func.lower(models.Device.serial).like(pattern),
            )
        )

    rows = db.execute(stmt).all()

    aggregated: OrderedDict[str, dict[str, Any]] = OrderedDict()

    for row in rows:
        mapping = row._mapping
        device_id = int(mapping["device_id"])
        sku = mapping["sku"]
        reference = _normalize_reference(sku, device_id)

        record = aggregated.get(reference)
        if record is None:
            record = {
                "reference": reference,
                "sku": sku,
                "product_name": mapping["name"],
                "device_ids": set(),
                "total_quantity": 0,
                "stores": {},
            }
            aggregated[reference] = record

        record["device_ids"].add(device_id)
        quantity = int(mapping["quantity"] or 0)
        record["total_quantity"] = int(record["total_quantity"]) + quantity
        _merge_store_entry(
            record["stores"],
            store_id=int(mapping["store_id"]),
            store_name=mapping["store_name"],
            quantity=quantity,
        )

    items: list[_AvailabilityRecord] = []
    for reference, record in aggregated.items():
        items.append(
            {
                "reference": reference,
                "sku": record.get("sku"),
                "product_name": record.get("product_name"),
                "device_ids": sorted(record["device_ids"]),
                "total_quantity": int(record["total_quantity"]),
                "stores": [
                    store
                    for store in sorted(
                        record["stores"].values(),
                        key=lambda candidate: (
                            -int(candidate["quantity"]),
                            candidate["store_name"],
                        ),
                    )
                ],
            }
        )
        if len(items) >= normalized_limit:
            break

    payload: _AvailabilityResponse = {
        "generated_at": datetime.now(timezone.utc),
        "items": items,
    }
    _CACHE.set(cache_key, copy.deepcopy(payload))
    return copy.deepcopy(payload)


def invalidate_inventory_availability_cache() -> None:
    """Limpia el cache en memoria de disponibilidad."""

    _CACHE.clear()


__all__ = [
    "get_inventory_availability",
    "invalidate_inventory_availability_cache",
]
