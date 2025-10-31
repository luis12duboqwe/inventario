"""Utilidades para exportar y depurar la bitácora de UI."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Iterable

from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..models import AuditUI
from ..schemas import AuditUIExportFormat

RETENTION_DAYS = 180


def _serialize_entry(entry: AuditUI) -> dict[str, object]:
    return {
        "id": entry.id,
        "ts": entry.ts.isoformat(),
        "userId": entry.user_id,
        "module": entry.module,
        "action": entry.action,
        "entityId": entry.entity_id,
        "meta": entry.meta or {},
    }


def _serialize_csv(entries: Iterable[AuditUI]) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=["id", "ts", "userId", "module", "action", "entityId", "meta"],
    )
    writer.writeheader()
    for entry in entries:
        serialized = _serialize_entry(entry)
        writer.writerow({**serialized, "meta": json.dumps(serialized["meta"], ensure_ascii=False)})
    return buffer.getvalue()


def _serialize_json(entries: Iterable[AuditUI]) -> str:
    payload = [_serialize_entry(entry) for entry in entries]
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def serialize_entries(entries: Iterable[AuditUI], export_format: AuditUIExportFormat) -> str:
    """Genera la representación indicada del conjunto de eventos."""

    events = list(entries)
    if export_format is AuditUIExportFormat.CSV:
        return _serialize_csv(events)
    return _serialize_json(events)


def cleanup_cutoff(*, retention_days: int = RETENTION_DAYS, reference: datetime | None = None) -> datetime:
    """Calcula el punto de corte para depuración de eventos antiguos."""

    now = reference or datetime.now(timezone.utc)
    return now - timedelta(days=retention_days)


def cleanup_expired_entries(db: Session, *, retention_days: int = RETENTION_DAYS) -> int:
    """Elimina entradas anteriores al corte de retención y devuelve cuántas filas se purgaron."""

    cutoff = cleanup_cutoff(retention_days=retention_days)
    result = db.execute(delete(AuditUI).where(AuditUI.ts < cutoff))
    db.commit()
    return int(result.rowcount or 0)


# // [PACK32-33-BE] Programar la ejecución periódica de cleanup_expired_entries cuando se habilite un scheduler.
