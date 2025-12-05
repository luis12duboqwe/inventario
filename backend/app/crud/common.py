"""Funciones comunes y utilidades para los módulos CRUD."""
from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from .. import models


def to_decimal(value: Decimal | float | int | None) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def log_audit_event(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | int,
    performed_by_id: int | None,
    details: str | Mapping[str, object] | None = None,
) -> models.AuditLog:
    entity_id_str = str(entity_id)
    if isinstance(details, Mapping):
        try:
            serialized_details = json.dumps(details, ensure_ascii=False)
        except TypeError:
            serialized_details = str(details)
    else:
        serialized_details = details

    audit_entry = models.AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id_str,
        performed_by_id=performed_by_id,
        details=serialized_details,
    )
    db.add(audit_entry)
    return audit_entry


def normalize_date_range(
    date_from: date | datetime | None, date_to: date | datetime | None
) -> tuple[datetime, datetime]:
    now = datetime.utcnow()

    if isinstance(date_from, datetime):
        start_dt = date_from
        if start_dt.time() == datetime.min.time():
            start_dt = start_dt.replace(
                hour=0, minute=0, second=0, microsecond=0)
    elif isinstance(date_from, date):
        start_dt = datetime.combine(date_from, datetime.min.time())
    else:
        start_dt = now - timedelta(days=30)

    if isinstance(date_to, datetime):
        end_dt = date_to
        if end_dt.time() == datetime.min.time():
            end_dt = end_dt.replace(
                hour=23, minute=59, second=59, microsecond=999999)
    elif isinstance(date_to, date):
        end_dt = datetime.combine(date_to, datetime.max.time())
    else:
        end_dt = now

    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    return start_dt, end_dt
