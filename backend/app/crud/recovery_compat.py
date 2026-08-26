"""Compatibilidad acotada para contratos perdidos durante la migración CRUD.

Las funciones de este módulo deben desaparecer cuando REC-0004/R3 incorpore cada
comportamiento directamente en su módulo canónico. Se mantienen separadas para
no volver a editar el archivo legacy recuperado.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from .. import models, schemas
from ..services.inventory_availability import invalidate_inventory_availability_cache
from .inventory import create_inventory_movement as _create_inventory_movement


def create_inventory_movement(
    db: Session,
    store_id: int,
    payload: schemas.MovementCreate,
    *,
    performed_by_id: int | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
) -> models.InventoryMovement:
    """Crea el movimiento e invalida la vista agregada de disponibilidad.

    El CRUD especializado actual modifica correctamente ``Device.quantity`` pero
    la extracción perdió la invalidación del cache de disponibilidad, dejando
    respuestas antiguas hasta vencer el TTL.
    """

    movement = _create_inventory_movement(
        db,
        store_id,
        payload,
        performed_by_id=performed_by_id,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    invalidate_inventory_availability_cache()
    return movement


def _utc_aware(value: datetime) -> datetime:
    """Normaliza fechas para comparaciones Python cuando SQLite pierde tzinfo."""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_payload_reservations(db: Session, payload: Any) -> None:
    for item in getattr(payload, "items", ()) or ():
        reservation_id = getattr(item, "reservation_id", None)
        if reservation_id is None:
            continue
        reservation = db.get(models.InventoryReservation, reservation_id)
        if reservation is None or reservation.expires_at is None:
            continue
        if reservation.expires_at.tzinfo is None:
            reservation.expires_at = _utc_aware(reservation.expires_at)


def create_reservation(
    db: Session,
    *,
    store_id: int,
    device_id: int,
    quantity: int,
    expires_at: datetime,
    reserved_by_id: int | None,
    reason: str,
) -> models.InventoryReservation:
    """Adapta la fecha de expiración al contrato UTC del CRUD recuperado."""

    from . import inventory as inventory_crud

    reservation = inventory_crud.create_reservation(
        db,
        store_id=store_id,
        device_id=device_id,
        quantity=quantity,
        expires_at=_utc_aware(expires_at),
        reserved_by_id=reserved_by_id,
        reason=reason,
    )
    if reservation.expires_at is not None and reservation.expires_at.tzinfo is None:
        reservation.expires_at = _utc_aware(reservation.expires_at)
    return reservation


def renew_reservation(
    db: Session,
    reservation_id: int,
    *,
    expires_at: datetime,
    performed_by_id: int | None,
    reason: str,
) -> models.InventoryReservation:
    """Renueva una reserva sin mezclar datetimes naive y aware."""

    from . import inventory as inventory_crud

    reservation = inventory_crud.renew_reservation(
        db,
        reservation_id,
        expires_at=_utc_aware(expires_at),
        performed_by_id=performed_by_id,
        reason=reason,
    )
    if reservation.expires_at is not None and reservation.expires_at.tzinfo is None:
        reservation.expires_at = _utc_aware(reservation.expires_at)
    return reservation


def create_sale(db: Session, payload, *args, **kwargs):
    """Normaliza reservas antes del flujo de venta legacy intacto."""

    from .. import crud_legacy

    _normalize_payload_reservations(db, payload)
    return crud_legacy.create_sale(db, payload, *args, **kwargs)


def create_transfer_order(db: Session, payload, *args, **kwargs):
    """Normaliza reservas antes del flujo extraído de transferencias."""

    from . import transfers as transfer_crud

    _normalize_payload_reservations(db, payload)
    return transfer_crud.create_transfer_order(db, payload, *args, **kwargs)


def log_dte_event(
    db: Session,
    *,
    document,
    event_type: str,
    status,
    detail: str | None,
    performed_by_id: int | None,
):
    """Puente REC-0004 para un modelo DTEEvent que nunca llegó al esquema.

    El estado fiscal sigue persistiendo en DTEDocument, Sale y la cola DTE. La
    tabla de eventos se recuperará como migración propia en lugar de inventarla
    durante el establecimiento del baseline.
    """

    return None


__all__ = [
    "create_inventory_movement",
    "create_reservation",
    "renew_reservation",
    "create_sale",
    "create_transfer_order",
    "log_dte_event",
]
