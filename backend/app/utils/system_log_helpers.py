"""Utilidades para logs del sistema y errores."""
from datetime import datetime, timezone
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
    before_date: datetime,
    nivel: str | None = None,
) -> int:
    """
    Elimina logs del sistema anteriores a una fecha.
    
    Args:
        db: Sesión de base de datos
        before_date: Eliminar logs anteriores a esta fecha
        nivel: Si se proporciona, solo eliminar logs de este nivel
        
    Returns:
        Número de registros eliminados
    """
    query = db.query(models.SystemLog).filter(
        models.SystemLog.timestamp < before_date
    )
    
    if nivel:
        query = query.filter(models.SystemLog.nivel == nivel)
    
    count = query.count()
    query.delete(synchronize_session=False)
    db.flush()
    
    return count
