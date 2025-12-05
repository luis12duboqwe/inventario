"""Servicio para gestionar delegación de tareas al agente en la nube."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.core.logging import logger as core_logger

from .. import models
from ..config import settings

logger = core_logger.bind(component=__name__)


def create_task(
    db: Session,
    task_type: models.CloudAgentTaskType,
    title: str,
    description: str | None = None,
    input_data: dict[str, Any] | None = None,
    priority: int = 5,
    max_retries: int = 3,
    created_by_id: int | None = None,
) -> models.CloudAgentTask:
    """
    Crear una nueva tarea para delegar al agente en la nube.

    Args:
        db: Sesión de base de datos
        task_type: Tipo de tarea a ejecutar
        title: Título descriptivo de la tarea
        description: Descripción detallada opcional
        input_data: Datos de entrada en formato diccionario
        priority: Prioridad de la tarea (1=alta, 10=baja)
        max_retries: Número máximo de reintentos permitidos
        created_by_id: ID del usuario que crea la tarea

    Returns:
        CloudAgentTask: La tarea creada
    """
    task = models.CloudAgentTask(
        task_type=task_type,
        title=title,
        description=description,
        input_data=json.dumps(input_data) if input_data else None,
        priority=priority,
        max_retries=max_retries,
        created_by_id=created_by_id,
        status=models.CloudAgentTaskStatus.PENDING,
        created_at=datetime.utcnow(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    logger.info(
        f"Tarea de nube creada: {task.id} ({task.task_type.value})",
        extra={"task_id": task.id, "task_type": task.task_type.value}
    )
    
    return task


def get_task(db: Session, task_id: int) -> models.CloudAgentTask | None:
    """Obtener una tarea por su ID."""
    return db.query(models.CloudAgentTask).filter(
        models.CloudAgentTask.id == task_id
    ).first()


def list_tasks(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    status: models.CloudAgentTaskStatus | None = None,
    task_type: models.CloudAgentTaskType | None = None,
    created_by_id: int | None = None,
) -> tuple[list[models.CloudAgentTask], int]:
    """
    Listar tareas con filtros opcionales.

    Returns:
        Tupla de (tareas, total_count)
    """
    query = db.query(models.CloudAgentTask)
    
    if status is not None:
        query = query.filter(models.CloudAgentTask.status == status)
    if task_type is not None:
        query = query.filter(models.CloudAgentTask.task_type == task_type)
    if created_by_id is not None:
        query = query.filter(models.CloudAgentTask.created_by_id == created_by_id)
    
    total = query.count()
    tasks = query.order_by(
        models.CloudAgentTask.priority,
        models.CloudAgentTask.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return tasks, total


def update_task_status(
    db: Session,
    task_id: int,
    status: models.CloudAgentTaskStatus,
    output_data: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> models.CloudAgentTask | None:
    """
    Actualizar el estado de una tarea.

    Args:
        db: Sesión de base de datos
        task_id: ID de la tarea
        status: Nuevo estado
        output_data: Datos de salida si la tarea se completó
        error_message: Mensaje de error si la tarea falló

    Returns:
        CloudAgentTask actualizada o None si no se encontró
    """
    task = get_task(db, task_id)
    if not task:
        return None
    
    task.status = status
    
    if status == models.CloudAgentTaskStatus.IN_PROGRESS and not task.started_at:
        task.started_at = datetime.utcnow()
    
    if status in (models.CloudAgentTaskStatus.COMPLETED, 
                  models.CloudAgentTaskStatus.FAILED,
                  models.CloudAgentTaskStatus.CANCELLED):
        task.completed_at = datetime.utcnow()
    
    if output_data is not None:
        task.output_data = json.dumps(output_data)
    
    if error_message is not None:
        task.error_message = error_message
    
    db.commit()
    db.refresh(task)
    
    logger.info(
        f"Tarea de nube actualizada: {task.id} -> {status.value}",
        extra={"task_id": task.id, "status": status.value}
    )
    
    return task


def cancel_task(db: Session, task_id: int) -> models.CloudAgentTask | None:
    """
    Cancelar una tarea pendiente o en progreso.

    Returns:
        CloudAgentTask cancelada o None si no se puede cancelar
    """
    task = get_task(db, task_id)
    if not task:
        return None
    
    # Solo se pueden cancelar tareas pendientes o en progreso
    if task.status not in (models.CloudAgentTaskStatus.PENDING,
                           models.CloudAgentTaskStatus.IN_PROGRESS):
        logger.warning(
            f"No se puede cancelar tarea {task_id} con estado {task.status.value}"
        )
        return None
    
    return update_task_status(
        db,
        task_id,
        models.CloudAgentTaskStatus.CANCELLED,
        error_message="Tarea cancelada por el usuario"
    )


def get_task_stats(db: Session) -> dict[str, Any]:
    """
    Obtener estadísticas agregadas de las tareas.

    Returns:
        Diccionario con estadísticas de tareas
    """
    stats = {
        "total_tasks": 0,
        "pending_tasks": 0,
        "in_progress_tasks": 0,
        "completed_tasks": 0,
        "failed_tasks": 0,
        "cancelled_tasks": 0,
        "avg_completion_time_seconds": None,
    }
    
    # Contar tareas por estado
    counts = db.query(
        models.CloudAgentTask.status,
        func.count(models.CloudAgentTask.id)
    ).group_by(models.CloudAgentTask.status).all()
    
    for status, count in counts:
        stats["total_tasks"] += count
        if status == models.CloudAgentTaskStatus.PENDING:
            stats["pending_tasks"] = count
        elif status == models.CloudAgentTaskStatus.IN_PROGRESS:
            stats["in_progress_tasks"] = count
        elif status == models.CloudAgentTaskStatus.COMPLETED:
            stats["completed_tasks"] = count
        elif status == models.CloudAgentTaskStatus.FAILED:
            stats["failed_tasks"] = count
        elif status == models.CloudAgentTaskStatus.CANCELLED:
            stats["cancelled_tasks"] = count
    
    # Calcular tiempo promedio de completado
    completed_tasks = db.query(models.CloudAgentTask).filter(
        models.CloudAgentTask.status == models.CloudAgentTaskStatus.COMPLETED,
        models.CloudAgentTask.started_at.isnot(None),
        models.CloudAgentTask.completed_at.isnot(None),
    ).all()
    
    if completed_tasks:
        total_seconds = sum(
            (task.completed_at - task.started_at).total_seconds()
            for task in completed_tasks
        )
        stats["avg_completion_time_seconds"] = total_seconds / len(completed_tasks)
    
    return stats


def retry_failed_tasks(db: Session, max_tasks: int = 10) -> list[models.CloudAgentTask]:
    """
    Reintentar tareas fallidas que no han excedido el máximo de reintentos.

    Args:
        db: Sesión de base de datos
        max_tasks: Número máximo de tareas a reintentar

    Returns:
        Lista de tareas que fueron reintentadas
    """
    if not settings.enable_cloud_agent:
        logger.debug("Cloud agent deshabilitado, saltando reintentos")
        return []
    
    # Buscar tareas fallidas elegibles para reintento
    failed_tasks = db.query(models.CloudAgentTask).filter(
        models.CloudAgentTask.status == models.CloudAgentTaskStatus.FAILED,
        models.CloudAgentTask.retry_count < models.CloudAgentTask.max_retries,
    ).order_by(
        models.CloudAgentTask.priority,
        models.CloudAgentTask.created_at
    ).limit(max_tasks).all()
    
    retried_tasks = []
    for task in failed_tasks:
        task.status = models.CloudAgentTaskStatus.PENDING
        task.retry_count += 1
        task.error_message = None
        db.commit()
        retried_tasks.append(task)
        
        logger.info(
            f"Reintentando tarea {task.id} (intento {task.retry_count}/{task.max_retries})"
        )
    
    return retried_tasks


def cleanup_old_tasks(db: Session, days_old: int = 30) -> int:
    """
    Limpiar tareas completadas o canceladas antiguas.

    Args:
        db: Sesión de base de datos
        days_old: Eliminar tareas más antiguas que este número de días

    Returns:
        Número de tareas eliminadas
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    
    deleted = db.query(models.CloudAgentTask).filter(
        models.CloudAgentTask.status.in_([
            models.CloudAgentTaskStatus.COMPLETED,
            models.CloudAgentTaskStatus.CANCELLED
        ]),
        models.CloudAgentTask.created_at < cutoff_date
    ).delete()
    
    db.commit()
    
    if deleted > 0:
        logger.info(f"Eliminadas {deleted} tareas antiguas de nube")
    
    return deleted
