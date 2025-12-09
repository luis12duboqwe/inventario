"""Utilidades para logs del sistema y errores."""
from datetime import datetime, timezone, timedelta
from typing import Any
from sqlalchemy.orm import Session

from .. import models


def create_system_log(
    db: Session,
    *,
    nivel: str,
    accion: str,
    modulo: str,
    usuario_id: int | None = None,
    detalles: dict[str, Any] | None = None,
) -> models.SystemLog:
    """
    Crea una entrada en el log del sistema.

    Args:
        db: Sesión de base de datos
        nivel: Nivel de severidad (info, warning, error, critical)
        accion: Acción registrada
        modulo: Módulo del sistema
        usuario_id: ID del usuario (opcional)
        detalles: Detalles adicionales en JSON (opcional)

    Returns:
        Entrada de log creada
    """
    log_entry = models.SystemLog(
        nivel=nivel,
        accion=accion,
        modulo=modulo,
        usuario_id=usuario_id,
        detalles=detalles or {},
        timestamp=datetime.now(timezone.utc),
    )
    db.add(log_entry)
    db.flush()
    return log_entry


def purge_system_logs(
    db: Session,
    *,
    retention_days: int,
    keep_critical: bool = False,
) -> int:
    """Elimina logs del sistema respetando retención y opcionalmente preserva críticos."""

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    query = db.query(models.SystemLog).filter(models.SystemLog.fecha < cutoff)

    if keep_critical:
        query = query.filter(models.SystemLog.nivel !=
                             models.SystemLogLevel.CRITICAL)

    removed = query.count()
    query.delete(synchronize_session=False)
    db.flush()

    return removed
