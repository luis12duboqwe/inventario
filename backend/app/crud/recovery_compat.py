"""Compatibilidad acotada para contratos perdidos durante la migración CRUD.

Las funciones de este módulo deben desaparecer cuando REC-0004/R3 incorpore cada
comportamiento directamente en su módulo canónico. Se mantienen separadas para
no volver a editar el archivo legacy recuperado.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy.orm import Session

from .. import models, schemas
from ..services.inventory_availability import invalidate_inventory_availability_cache
from .common import to_decimal
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
    """Crea el movimiento e invalida la vista agregada de disponibilidad."""

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


def _recalculate_sale_price(device: models.Device) -> None:
    """Restaura el contrato histórico: costo/margen determinan precio de venta."""

    base_cost = to_decimal(device.costo_unitario)
    margin = to_decimal(device.margen_porcentaje)
    sale_factor = Decimal("1") + (margin / Decimal("100"))
    recalculated = (base_cost * sale_factor).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    device.unit_price = recalculated
    device.precio_venta = recalculated


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


def release_reservation(
    db: Session,
    reservation_id: int,
    *,
    performed_by_id: int | None,
    reason: str | None = None,
    target_state: models.InventoryState = models.InventoryState.CANCELADO,
    reference_type: str | None = None,
    reference_id: str | None = None,
) -> models.InventoryReservation:
    """Conserva el resolved_at existente y registra además consumed_at al vender."""

    from . import inventory as inventory_crud

    reservation = inventory_crud.release_reservation(
        db,
        reservation_id,
        performed_by_id=performed_by_id,
        reason=reason,
        target_state=target_state,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    if target_state == models.InventoryState.CONSUMIDO and reservation.consumed_at is None:
        reservation.consumed_at = datetime.now(timezone.utc)
        db.add(reservation)
        db.flush()
        db.refresh(reservation)
    return reservation


def create_sale(db: Session, payload, *args, **kwargs):
    """Normaliza reservas y conserva el flujo especializado actual de ventas."""

    from . import sales as sales_crud

    _normalize_payload_reservations(db, payload)
    return sales_crud.create_sale(db, payload, *args, **kwargs)


def create_transfer_order(db: Session, payload, *args, **kwargs):
    """Normaliza reservas antes del flujo extraído de transferencias."""

    from . import transfers as transfer_crud

    _normalize_payload_reservations(db, payload)
    return transfer_crud.create_transfer_order(db, payload, *args, **kwargs)


def register_pos_sale(
    db: Session,
    payload: schemas.POSSaleRequest,
    *,
    performed_by_id: int | None = None,
    sold_by_id: int | None = None,
    reason: str | None = None,
):
    """Acepta ambas firmas POS y delega al flujo legacy completo recuperado."""

    from .. import crud_legacy

    actor_id = performed_by_id if performed_by_id is not None else sold_by_id
    if actor_id is None:
        raise ValueError("pos_operator_required")
    return crud_legacy.register_pos_sale(
        db,
        payload,
        performed_by_id=actor_id,
        reason=reason,
    )


def log_dte_event(
    db: Session,
    *,
    document,
    event_type: str,
    status,
    detail: str | None,
    performed_by_id: int | None,
):
    """Puente REC-0004 para un modelo DTEEvent que nunca llegó al esquema."""

    return None


__all__ = [
    "create_inventory_movement",
    "create_reservation",
    "renew_reservation",
    "release_reservation",
    "create_sale",
    "create_transfer_order",
    "register_pos_sale",
    "log_dte_event",
]
