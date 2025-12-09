from __future__ import annotations

from sqlalchemy.orm import Session

from .. import crud, models, schemas


def _actor_name(user: models.User | None) -> str | None:
    if user is None:
        return None
    return user.full_name or user.username


def _serialize_history(event: models.RMAEvent) -> schemas.RMAHistoryEntry:
    return schemas.RMAHistoryEntry(
        id=event.id,
        status=schemas.RMAStatus(event.status.value),
        message=event.message,
        created_at=event.created_at,
        created_by_id=event.created_by_id,
        created_by_name=_actor_name(event.created_by),
    )


def _serialize_rma(rma: models.RMARequest) -> schemas.RMARecord:
    return schemas.RMARecord(
        id=rma.id,
        status=schemas.RMAStatus(rma.status.value),
        store_id=rma.store_id,
        device_id=rma.device_id,
        disposition=rma.disposition,
        notes=rma.notes,
        sale_return_id=rma.sale_return_id,
        purchase_return_id=rma.purchase_return_id,
        repair_order_id=rma.repair_order_id,
        replacement_sale_id=rma.replacement_sale_id,
        history=[_serialize_history(event).model_dump()
                 for event in rma.history],
    )


def create_rma(db: Session, payload: schemas.RMACreate, *, created_by_id: int) -> schemas.RMARecord:
    rma = crud.create_rma_request(db, payload, created_by_id=created_by_id)
    return _serialize_rma(rma)


def authorize_rma(
    db: Session,
    rma_id: int,
    *,
    notes: str | None,
    actor_id: int,
) -> schemas.RMARecord:
    rma = crud.authorize_rma_request(
        db, rma_id, notes=notes, actor_id=actor_id)
    return _serialize_rma(rma)


def process_rma(
    db: Session,
    rma_id: int,
    *,
    payload: schemas.RMAUpdate,
    actor_id: int,
) -> schemas.RMARecord:
    rma = crud.process_rma_request(
        db, rma_id, payload=payload, actor_id=actor_id)
    return _serialize_rma(rma)


def close_rma(
    db: Session,
    rma_id: int,
    *,
    payload: schemas.RMAUpdate,
    actor_id: int,
) -> schemas.RMARecord:
    rma = crud.close_rma_request(
        db, rma_id, payload=payload, actor_id=actor_id)
    return _serialize_rma(rma)


def get_rma(db: Session, rma_id: int) -> schemas.RMARecord:
    rma = crud.get_rma_request(db, rma_id)
    return _serialize_rma(rma)
