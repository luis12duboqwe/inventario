"""Operaciones CRUD para Facturación Electrónica (DTE).

Migrado desde crud_legacy.py - Fase 2, Incremento 4
Contiene funciones para gestión de documentos tributarios electrónicos.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app import models, schemas

# Avoid circular imports
if TYPE_CHECKING:
    from backend.app import crud_legacy

__all__ = [
    'create_dte_authorization',
    'list_dte_authorizations',
    'get_dte_authorization',
    'update_dte_authorization',
    'reserve_dte_folio',
    'register_dte_document',
    'log_dte_event',
    'list_dte_documents',
    'get_dte_document',
    'register_dte_ack',
    'enqueue_dte_dispatch',
    'mark_dte_dispatch_sent',
    'list_dte_dispatch_queue',
]
def create_dte_authorization(
    db: Session,
    payload: schemas.DTEAuthorizationCreate,
) -> models.DTEAuthorization:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    document_type = payload.document_type.strip().upper()
    serie = payload.serie.strip().upper()
    store_id = payload.store_id

    statement = select(models.DTEAuthorization).where(
        func.upper(models.DTEAuthorization.document_type) == document_type,
        func.upper(models.DTEAuthorization.serie) == serie,
        models.DTEAuthorization.range_start <= payload.range_end,
        models.DTEAuthorization.range_end >= payload.range_start,
    )
    if store_id is None:
        statement = statement.where(models.DTEAuthorization.store_id.is_(None))
    else:
        statement = statement.where(
            models.DTEAuthorization.store_id == store_id)

    conflict = db.scalars(statement).first()
    if conflict:
        raise ValueError("dte_authorization_conflict")

    authorization = models.DTEAuthorization(
        store_id=store_id,
        document_type=document_type,
        serie=serie,
        range_start=payload.range_start,
        range_end=payload.range_end,
        current_number=payload.range_start,
        cai=payload.cai,
        expiration_date=payload.expiration_date,
        active=payload.active,
        notes=payload.notes,
    )
    db.add(authorization)
    db.flush()
    db.refresh(authorization)
    return authorization



def list_dte_authorizations(
    db: Session,
    *,
    store_id: int | None = None,
    document_type: str | None = None,
    active: bool | None = None,
) -> list[models.DTEAuthorization]:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    statement = (
        select(models.DTEAuthorization)
        .order_by(models.DTEAuthorization.created_at.desc())
    )
    if store_id is not None:
        statement = statement.where(
            or_(
                models.DTEAuthorization.store_id == store_id,
                models.DTEAuthorization.store_id.is_(None),
            )
        )
    if document_type:
        statement = statement.where(
            func.upper(models.DTEAuthorization.document_type)
            == document_type.strip().upper()
        )
    if active is not None:
        statement = statement.where(models.DTEAuthorization.active.is_(active))
    return list(db.scalars(statement))



def get_dte_authorization(db: Session, authorization_id: int) -> models.DTEAuthorization:
    authorization = db.get(models.DTEAuthorization, authorization_id)
    if authorization is None:
        raise LookupError("dte_authorization_not_found")
    return authorization



def update_dte_authorization(
    db: Session,
    authorization_id: int,
    payload: schemas.DTEAuthorizationUpdate,
) -> models.DTEAuthorization:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    authorization = get_dte_authorization(db, authorization_id)

    if payload.expiration_date is not None:
        authorization.expiration_date = payload.expiration_date
    if payload.notes is not None:
        authorization.notes = payload.notes
    if payload.active is not None:
        authorization.active = payload.active

    db.add(authorization)
    db.flush()
    db.refresh(authorization)
    return authorization



def reserve_dte_folio(
    db: Session,
    authorization: models.DTEAuthorization,
) -> int:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    next_number = authorization.current_number
    if next_number < authorization.range_start:
        next_number = authorization.range_start
    if next_number > authorization.range_end:
        raise ValueError("dte_authorization_exhausted")

    authorization.current_number = next_number + 1
    db.add(authorization)
    db.flush()
    db.refresh(authorization)
    return next_number



def register_dte_document(
    db: Session,
    *,
    sale: models.Sale,
    authorization: models.DTEAuthorization,
    xml_content: str,
    signature: str,
    control_number: str,
    correlative: int,
    reference_code: str | None,
) -> models.DTEDocument:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    document = models.DTEDocument(
        sale_id=sale.id,
        authorization_id=authorization.id if authorization else None,
        document_type=authorization.document_type,
        serie=authorization.serie,
        correlative=correlative,
        control_number=control_number,
        cai=authorization.cai,
        xml_content=xml_content,
        signature=signature,
        reference_code=reference_code,
    )
    sale.dte_status = models.DTEStatus.PENDIENTE
    sale.dte_reference = control_number
    db.add(document)
    db.add(sale)
    db.flush()
    db.refresh(document)
    return document



def log_dte_event(
    db: Session,
    *,
    document: models.DTEDocument,
    event_type: str,
    status: models.DTEStatus,
    detail: str | None,
    performed_by_id: int | None,
) -> models.DTEEvent:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    event = models.DTEEvent(
        document=document,
        event_type=event_type,
        status=status,
        detail=detail,
        performed_by_id=performed_by_id,
    )
    db.add(event)
    db.flush()
    db.refresh(event)
    return event



def list_dte_documents(
    db: Session,
    *,
    store_id: int | None = None,
    sale_id: int | None = None,
    status: models.DTEStatus | str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[models.DTEDocument]:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    safe_limit = None if limit is None else max(1, min(limit, 200))
    statement = (
        select(models.DTEDocument)
        .options(
            joinedload(models.DTEDocument.sale).joinedload(models.Sale.store),
            joinedload(models.DTEDocument.authorization),
            selectinload(models.DTEDocument.events),
            selectinload(models.DTEDocument.dispatch_entries),
        )
        .order_by(models.DTEDocument.created_at.desc())
    )
    if store_id is not None:
        statement = statement.join(models.DTEDocument.sale).where(
            models.Sale.store_id == store_id
        )
    if sale_id is not None:
        statement = statement.where(models.DTEDocument.sale_id == sale_id)
    if status is not None:
        enum_status = (
            status
            if isinstance(status, models.DTEStatus)
            else models.DTEStatus(status)
        )
        statement = statement.where(models.DTEDocument.status == enum_status)
    if offset:
        statement = statement.offset(offset)
    if safe_limit is not None:
        statement = statement.limit(safe_limit)
    return list(db.scalars(statement))



def get_dte_document(db: Session, document_id: int) -> models.DTEDocument:
    document = db.get(models.DTEDocument, document_id)
    if document is None:
        raise LookupError("dte_document_not_found")
    return document



def register_dte_ack(
    db: Session,
    *,
    document: models.DTEDocument,
    status: models.DTEStatus,
    code: str | None,
    detail: str | None,
    received_at: datetime,
) -> models.DTEDocument:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    ack_time = received_at
    if ack_time.tzinfo is not None:
        ack_time = ack_time.astimezone(timezone.utc).replace(tzinfo=None)
    document.status = status
    document.ack_code = code
    document.ack_message = detail
    document.acknowledged_at = ack_time
    if document.sale:
        document.sale.dte_status = status
        if code:
            document.sale.dte_reference = code
    db.add(document)
    if document.sale:
        db.add(document.sale)
    db.flush()
    db.refresh(document)
    return document



def enqueue_dte_dispatch(
    db: Session,
    *,
    document: models.DTEDocument,
    error_message: str | None,
) -> models.DTEDispatchQueue:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    existing = db.scalar(
        select(models.DTEDispatchQueue).where(
            models.DTEDispatchQueue.document_id == document.id
        )
    )
    now = datetime.now(timezone.utc)
    if existing:
        existing.status = models.DTEDispatchStatus.PENDING
        existing.last_error = error_message
        existing.scheduled_at = now
        existing.updated_at = now
        if existing.attempts <= 0:
            existing.attempts = 0
        existing.document = document
        db.add(existing)
        entry = existing
    else:
        entry = models.DTEDispatchQueue(
            document=document,
            document_id=document.id,
            status=models.DTEDispatchStatus.PENDING,
            attempts=0,
            last_error=error_message,
            scheduled_at=now,
        )
        db.add(entry)
    db.flush()
    db.refresh(entry)
    return entry



def mark_dte_dispatch_sent(
    db: Session,
    *,
    document: models.DTEDocument,
    error_message: str | None,
) -> models.DTEDispatchQueue:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    entry = db.scalar(
        select(models.DTEDispatchQueue).where(
            models.DTEDispatchQueue.document_id == document.id
        )
    )
    now = datetime.now(timezone.utc)
    if entry is None:
        entry = models.DTEDispatchQueue(
            document=document,
            document_id=document.id,
            status=models.DTEDispatchStatus.SENT,
            attempts=1,
            last_error=error_message,
            scheduled_at=now,
        )
    else:
        entry.status = models.DTEDispatchStatus.SENT
        entry.attempts = entry.attempts + 1
        entry.last_error = error_message
        entry.updated_at = now
    entry.document = document
    document.sent_at = now
    db.add(entry)
    db.add(document)
    db.flush()
    db.refresh(entry)
    db.refresh(document)
    return entry



def list_dte_dispatch_queue(
    db: Session,
    *,
    statuses: Iterable[models.DTEDispatchStatus] | None = None,
) -> list[models.DTEDispatchQueue]:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    statement = (
        select(models.DTEDispatchQueue)
        .options(joinedload(models.DTEDispatchQueue.document))
        .order_by(models.DTEDispatchQueue.created_at.desc())
    )
    if statuses:
        statement = statement.where(
            models.DTEDispatchQueue.status.in_(tuple(statuses)))
    return list(db.scalars(statement))



