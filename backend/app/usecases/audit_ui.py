"""Casos de uso para coordinar auditoría UI entre routers y CRUD."""
from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from datetime import date, datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core.transactions import flush_session
from ..services import audit_ui as audit_ui_service

RangeNormalizer = Callable[
    [date | datetime | None, date | datetime | None],
    tuple[datetime | None, datetime | None],
]
Serializer = Callable[[Iterable[models.AuditUI], schemas.AuditUIExportFormat], str]


def create_entries(
    db: Session,
    *,
    items: Sequence[schemas.AuditUIBulkItem],
) -> int:
    """Crea múltiples entradas de auditoría UI en una sola transacción."""

    records = [
        models.AuditUI(
            ts=item.ts,
            user_id=item.user_id,
            module=item.module,
            action=item.action,
            entity_id=item.entity_id,
            meta=item.meta,
        )
        for item in items
    ]
    db.add_all(records)
    flush_session(db)
    return len(records)


def list_entries(
    db: Session,
    *,
    limit: int,
    offset: int,
    date_from: date | datetime | None = None,
    date_to: date | datetime | None = None,
    user_id: str | None = None,
    module: str | None = None,
    range_normalizer: RangeNormalizer = audit_ui_service.normalize_range,
) -> tuple[list[models.AuditUI], int]:
    """Lista eventos de auditoría UI aplicando filtros y totalización."""

    stmt = select(models.AuditUI).order_by(desc(models.AuditUI.ts)).limit(limit).offset(offset)
    count_stmt = select(func.count()).select_from(models.AuditUI)

    normalized_from, normalized_to = range_normalizer(date_from, date_to)

    if normalized_from is not None:
        stmt = stmt.where(models.AuditUI.ts >= normalized_from)
        count_stmt = count_stmt.where(models.AuditUI.ts >= normalized_from)
    if normalized_to is not None:
        stmt = stmt.where(models.AuditUI.ts <= normalized_to)
        count_stmt = count_stmt.where(models.AuditUI.ts <= normalized_to)
    if user_id:
        stmt = stmt.where(models.AuditUI.user_id == user_id)
        count_stmt = count_stmt.where(models.AuditUI.user_id == user_id)
    if module:
        stmt = stmt.where(models.AuditUI.module == module)
        count_stmt = count_stmt.where(models.AuditUI.module == module)

    entries = list(db.scalars(stmt))
    total = db.scalar(count_stmt) or 0
    return entries, int(total)


def export_entries(
    db: Session,
    *,
    export_format: schemas.AuditUIExportFormat,
    date_from: date | datetime | None = None,
    date_to: date | datetime | None = None,
    user_id: str | None = None,
    module: str | None = None,
    limit: int | None = None,
    range_normalizer: RangeNormalizer = audit_ui_service.normalize_range,
    serializer: Serializer = audit_ui_service.serialize_entries,
) -> str:
    """Genera una exportación serializada en el formato solicitado."""

    stmt = select(models.AuditUI).order_by(desc(models.AuditUI.ts))

    normalized_from, normalized_to = range_normalizer(date_from, date_to)

    if normalized_from is not None:
        stmt = stmt.where(models.AuditUI.ts >= normalized_from)
    if normalized_to is not None:
        stmt = stmt.where(models.AuditUI.ts <= normalized_to)
    if user_id:
        stmt = stmt.where(models.AuditUI.user_id == user_id)
    if module:
        stmt = stmt.where(models.AuditUI.module == module)
    if limit is not None:
        stmt = stmt.limit(limit)

    entries = list(db.scalars(stmt))
    return serializer(entries, export_format)


__all__ = [
    "create_entries",
    "list_entries",
    "export_entries",
]
