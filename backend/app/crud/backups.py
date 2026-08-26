"""CRUD de metadatos de respaldos recuperado tras la corrupción de crud_legacy.

Este módulo conserva el contrato vigente de BackupJob (filename/file_path no nulos)
sin volver a introducir los cuerpos parcialmente migrados de crud_legacy.py.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from .. import models
from ..core.transactions import flush_session, transactional_session
from .audit import log_audit_event


def create_backup_job(
    db: Session,
    *,
    mode: models.BackupMode,
    pdf_path: str,
    archive_path: str,
    json_path: str,
    sql_path: str,
    config_path: str,
    metadata_path: str,
    critical_directory: str,
    components: list[str],
    total_size_bytes: int,
    notes: str | None,
    triggered_by_id: int | None,
    reason: str | None = None,
) -> models.BackupJob:
    """Persiste un BackupJob usando el esquema actual de la tabla.

    La implementación histórica restaurada es anterior a los campos obligatorios
    ``filename`` y ``file_path``. El código vigente antes de la corrupción ya los
    derivaba del ZIP, por lo que mantenemos aquí ese comportamiento.
    """

    archive_file = Path(archive_path)
    filename = archive_file.name
    archive_size = archive_file.stat().st_size if archive_file.exists() else 0
    now = datetime.now(timezone.utc)

    job = models.BackupJob(
        filename=filename,
        file_path=str(archive_file),
        mode=mode,
        pdf_path=pdf_path,
        archive_path=archive_path,
        json_path=json_path,
        sql_path=sql_path,
        config_path=config_path,
        metadata_path=metadata_path,
        critical_directory=critical_directory,
        components=components,
        total_size_bytes=total_size_bytes,
        file_size_bytes=archive_size,
        notes=notes,
        triggered_by_id=triggered_by_id,
        executed_at=now,
        updated_at=now,
    )

    with transactional_session(db):
        db.add(job)
        flush_session(db)

        component_list = ",".join(components)
        details = (
            f"modo={mode.value}; tamaño={total_size_bytes}; "
            f"componentes={component_list}; archivos={archive_path}"
        )
        if reason:
            details = f"{details}; motivo={reason}"
        log_audit_event(
            db,
            action="backup_generated",
            entity_type="backup",
            entity_id=str(job.id),
            performed_by_id=triggered_by_id,
            details=details,
        )
        db.refresh(job)

    return job


__all__ = ["create_backup_job"]
