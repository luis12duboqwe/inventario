"""Servicios de conveniencia para registrar y consultar auditoría."""
from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy.orm import Session

from .. import schemas
from ..crud import get_last_audit_entries, log_audit_event
from ..utils import audit_trail as audit_trail_utils


def record_audit_event(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | int,
    user_id: int | None,
    description: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> schemas.AuditTrailInfo:
    """Crea un registro de auditoría y devuelve la representación serializada."""

    details: dict[str, Any] | None = None
    if description:
        details = {"description": description}
    if metadata:
        if details is None:
            details = {"metadata": metadata}
        else:
            details["metadata"] = metadata

    log_entry = log_audit_event(
        db,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        performed_by_id=user_id,
        details=details,
    )
    return audit_trail_utils.to_audit_trail(log_entry)


def get_last_audit_trails(
    db: Session,
    *,
    entity_type: str,
    entity_ids: Iterable[int | str],
) -> dict[str, schemas.AuditTrailInfo]:
    """Recupera la última acción de auditoría por entidad normalizada."""

    logs = get_last_audit_entries(db, entity_type=entity_type, entity_ids=entity_ids)
    return {
        key: audit_trail_utils.to_audit_trail(log)
        for key, log in logs.items()
    }


__all__ = ["get_last_audit_trails", "record_audit_event"]
