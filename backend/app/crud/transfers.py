"""Operaciones CRUD para Transferencias entre Sucursales.

Migrado desde crud_legacy.py - Fase 2, Incremento 3
Contiene funciones para gestión de órdenes de transferencia entre tiendas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app import models, schemas
from backend.app.core.transactions import flush_session, transactional_session

# Import from other crud modules
from backend.app.crud.stores import get_store
from backend.app.crud.devices import get_device

# Avoid circular imports
if TYPE_CHECKING:
    from backend.app import crud_legacy

__all__ = [
    'create_transfer_order',
    'get_transfer_order',
    'dispatch_transfer_order',
    'receive_transfer_order',
    'cancel_transfer_order',
    'list_transfer_orders',
]
def create_transfer_order(
    db: Session,
    payload: schemas.TransferOrderCreate,
    *,
    requested_by_id: int,
) -> models.TransferOrder:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    if payload.origin_store_id == payload.destination_store_id:
        raise ValueError("transfer_same_store")

    origin_store = get_store(db, payload.origin_store_id)
    destination_store = get_store(db, payload.destination_store_id)

    try:
        _require_store_permission(
            db,
            user_id=requested_by_id,
            store_id=origin_store.id,
            permission="create",
        )
    except PermissionError:
        normalized_reason = (payload.reason or "").strip()
        if len(normalized_reason) < 5 or not _user_can_override_transfer(
            db, user_id=requested_by_id, store_id=origin_store.id
        ):
            raise

    if not payload.items:
        raise ValueError("transfer_items_required")

    order = models.TransferOrder(
        origin_store_id=origin_store.id,
        destination_store_id=destination_store.id,
        status=models.TransferStatus.SOLICITADA,
        requested_by_id=requested_by_id,
        reason=payload.reason,
    )
    with transactional_session(db):
        db.add(order)
        flush_session(db)

        expire_reservations(
            db, store_id=origin_store.id, device_ids=[
                item.device_id for item in payload.items]
        )

        for item in payload.items:
            device = get_device(db, origin_store.id, item.device_id)
            if item.quantity <= 0:
                raise ValueError("transfer_invalid_quantity")
            reservation_id = getattr(item, "reservation_id", None)
            reservation = None
            if reservation_id is not None:
                reservation = get_inventory_reservation(db, reservation_id)
                if reservation.store_id != origin_store.id:
                    raise ValueError("reservation_store_mismatch")
                if reservation.device_id != device.id:
                    raise ValueError("reservation_device_mismatch")
                if reservation.status != models.InventoryState.RESERVADO:
                    raise ValueError("reservation_not_active")
                if reservation.quantity != item.quantity:
                    raise ValueError("reservation_quantity_mismatch")
                if reservation.expires_at <= datetime.now(timezone.utc):
                    raise ValueError("reservation_expired")
            order_item = models.TransferOrderItem(
                transfer_order=order,
                device=device,
                quantity=item.quantity,
                reservation_id=reservation.id if reservation is not None else None,
            )
            db.add(order_item)

        flush_session(db)
        _log_action(
            db,
            action="transfer_created",
            entity_type="transfer_order",
            entity_id=str(order.id),
            performed_by_id=requested_by_id,
            details=json.dumps({
                "origin": origin_store.id,
                "destination": destination_store.id,
                "reason": payload.reason,
            }),
        )
    db.refresh(order)
    order = get_transfer_order(db, order.id)
    enqueue_sync_outbox(
        db,
        entity_type="transfer_order",
        entity_id=str(order.id),
        operation="UPSERT",
        payload=transfer_order_payload(order),
        priority=models.SyncOutboxPriority.HIGH,
    )
    return order



def get_transfer_order(db: Session, transfer_id: int) -> models.TransferOrder:
    statement = (
        select(models.TransferOrder)
        .options(
            joinedload(models.TransferOrder.items).joinedload(
                models.TransferOrderItem.device),
            joinedload(models.TransferOrder.origin_store),
            joinedload(models.TransferOrder.destination_store),
        )
        .where(models.TransferOrder.id == transfer_id)
    )
    try:
        return db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("transfer_not_found") from exc



def dispatch_transfer_order(
    db: Session,
    transfer_id: int,
    *,
    performed_by_id: int,
    reason: str | None,
) -> models.TransferOrder:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    order = get_transfer_order(db, transfer_id)
    if order.status not in {models.TransferStatus.SOLICITADA}:
        raise ValueError("transfer_invalid_transition")

    _require_store_permission(
        db,
        user_id=performed_by_id,
        store_id=order.origin_store_id,
        permission="create",
    )

    with transactional_session(db):
        _apply_transfer_dispatch(
            db, order, performed_by_id=performed_by_id, reason=reason
        )
        order.status = models.TransferStatus.EN_TRANSITO
        order.dispatched_by_id = performed_by_id
        order.dispatched_at = datetime.now(timezone.utc)
        order.reason = reason or order.reason

        flush_session(db)

        _log_action(
            db,
            action="transfer_dispatched",
            entity_type="transfer_order",
            entity_id=str(order.id),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {"status": order.status.value, "reason": reason}),
        )

        db.refresh(order)
    order = get_transfer_order(db, order.id)
    enqueue_sync_outbox(
        db,
        entity_type="transfer_order",
        entity_id=str(order.id),
        operation="UPSERT",
        payload=transfer_order_payload(order),
        priority=models.SyncOutboxPriority.HIGH,
    )
    return order



def receive_transfer_order(
    db: Session,
    transfer_id: int,
    *,
    performed_by_id: int,
    reason: str | None,
    items: list[schemas.TransferReceptionItem] | None = None,
    use_transaction: bool = True,
) -> models.TransferOrder:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    order = get_transfer_order(db, transfer_id)
    if order.status not in {models.TransferStatus.SOLICITADA, models.TransferStatus.EN_TRANSITO}:
        raise ValueError("transfer_invalid_transition")

    _require_store_permission(
        db,
        user_id=performed_by_id,
        store_id=order.destination_store_id,
        permission="receive",
    )

    def _receive_transfer() -> models.TransferOrder:
        if not any(item.dispatched_quantity > 0 for item in order.items):
            _apply_transfer_dispatch(
                db, order, performed_by_id=performed_by_id, reason=reason
            )

        reception_map = _normalize_reception_quantities(order, items)
        _apply_transfer_reception(
            db, order, performed_by_id=performed_by_id, received_map=reception_map
        )

        order.status = models.TransferStatus.RECIBIDA
        order.received_by_id = performed_by_id
        order.received_at = datetime.now(timezone.utc)
        order.reason = reason or order.reason

        flush_session(db)

        _log_action(
            db,
            action="transfer_received",
            entity_type="transfer_order",
            entity_id=str(order.id),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {"status": order.status.value, "reason": reason}),
        )

        db.refresh(order)
        return order

    if use_transaction:
        with transactional_session(db):
            processed_order = _receive_transfer()
    else:
        processed_order = _receive_transfer()
    processed_order = get_transfer_order(db, processed_order.id)
    enqueue_sync_outbox(
        db,
        entity_type="transfer_order",
        entity_id=str(processed_order.id),
        operation="UPSERT",
        payload=transfer_order_payload(processed_order),
        priority=models.SyncOutboxPriority.HIGH,
    )
    return processed_order



def cancel_transfer_order(
    db: Session,
    transfer_id: int,
    *,
    performed_by_id: int,
    reason: str | None,
) -> models.TransferOrder:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    order = get_transfer_order(db, transfer_id)
    if order.status in {models.TransferStatus.RECIBIDA, models.TransferStatus.CANCELADA}:
        raise ValueError("transfer_invalid_transition")

    _require_store_permission(
        db,
        user_id=performed_by_id,
        store_id=order.origin_store_id,
        permission="create",
    )

    with transactional_session(db):
        order.status = models.TransferStatus.CANCELADA
        order.cancelled_by_id = performed_by_id
        order.cancelled_at = datetime.now(timezone.utc)
        order.reason = reason or order.reason

        flush_session(db)

        _log_action(
            db,
            action="transfer_cancelled",
            entity_type="transfer_order",
            entity_id=str(order.id),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {"status": order.status.value, "reason": reason}),
        )

        db.refresh(order)
    order = get_transfer_order(db, order.id)
    enqueue_sync_outbox(
        db,
        entity_type="transfer_order",
        entity_id=str(order.id),
        operation="UPSERT",
        payload=transfer_order_payload(order),
        priority=models.SyncOutboxPriority.HIGH,
    )
    return order



def list_transfer_orders(
    db: Session,
    *,
    store_id: int | None = None,
    origin_store_id: int | None = None,
    destination_store_id: int | None = None,
    status: models.TransferStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int | None = 50,
    offset: int = 0,
) -> list[models.TransferOrder]:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    statement = (
        select(models.TransferOrder)
        .options(
            joinedload(models.TransferOrder.items).joinedload(
                models.TransferOrderItem.device),
            joinedload(models.TransferOrder.origin_store),
            joinedload(models.TransferOrder.destination_store),
            joinedload(models.TransferOrder.requested_by),
            joinedload(models.TransferOrder.dispatched_by),
            joinedload(models.TransferOrder.received_by),
            joinedload(models.TransferOrder.cancelled_by),
        )
        .order_by(models.TransferOrder.created_at.desc())
    )
    if store_id is not None:
        statement = statement.where(
            (models.TransferOrder.origin_store_id == store_id)
            | (models.TransferOrder.destination_store_id == store_id)
        )
    if origin_store_id is not None:
        statement = statement.where(
            models.TransferOrder.origin_store_id == origin_store_id)
    if destination_store_id is not None:
        statement = statement.where(
            models.TransferOrder.destination_store_id == destination_store_id)
    if status is not None:
        statement = statement.where(models.TransferOrder.status == status)
    if date_from is not None:
        statement = statement.where(
            models.TransferOrder.created_at >= date_from)
    if date_to is not None:
        statement = statement.where(models.TransferOrder.created_at <= date_to)
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement).unique())



