"""Servicios para la búsqueda avanzada del catálogo pro de dispositivos."""
from __future__ import annotations

from typing import Tuple

from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..audit_logger import audit_event


def _serialize_filters(filters: schemas.DeviceSearchFilters) -> dict[str, object]:
    """Convierte los filtros aplicados a un formato serializable."""

    serialized = filters.model_dump(exclude_none=True)
    # Evita incluir llaves vacías en auditoría.
    return {key: value for key, value in serialized.items() if value not in ("", None)}


def advanced_catalog_search(
    db: Session,
    *,
    filters: schemas.DeviceSearchFilters,
    limit: int,
    offset: int,
    requested_by: models.User | None,
) -> Tuple[list[schemas.CatalogProDeviceResponse], int]:
    """Ejecuta la búsqueda avanzada del catálogo y registra auditoría."""

    total = crud.count_devices_matching_filters(db, filters)
    devices = crud.search_devices(db, filters, limit=limit, offset=offset)

    results: list[schemas.CatalogProDeviceResponse] = []
    for device in devices:
        base = schemas.DeviceResponse.model_validate(device, from_attributes=True)
        results.append(
            schemas.CatalogProDeviceResponse(
                **base.model_dump(),
                store_name=device.store.name if device.store else "",
            )
        )

    filter_payload = _serialize_filters(filters)
    performed_by_id = getattr(requested_by, "id", None)

    audit_details = {
        "filters": filter_payload,
        "results": len(results),
        "total": total,
    }
    audit_identifier = (
        f"catalog_search:{performed_by_id}" if performed_by_id is not None else "catalog_search:anon"
    )

    crud.log_audit_event(
        db,
        action="inventory_catalog_search",
        entity_type="inventory",
        entity_id=audit_identifier,
        performed_by_id=performed_by_id,
        details=audit_details,
    )
    audit_event(
        user_id=str(performed_by_id) if performed_by_id is not None else None,
        action="inventory_catalog_search",
        resource="inventory.catalog",
        reason=None,
        extra=audit_details,
    )

    return results, total


__all__ = ["advanced_catalog_search"]
