"""Router para endpoints de delegación al agente en la nube."""
from __future__ import annotations

import json
import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..database import get_db
from ..security import get_current_user, require_roles
from ..core.roles import ADMIN
from ..services import cloud_agent

router = APIRouter(
    prefix="/cloud",
    tags=["cloud-agent"],
)


def _check_cloud_agent_enabled() -> None:
    """Verificar que el feature flag de cloud agent esté habilitado."""
    if not settings.enable_cloud_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de agente en la nube no está habilitado"
        )


@router.post(
    "/delegate",
    response_model=schemas.CloudAgentTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Delegar tarea al agente en la nube",
)
async def delegate_task(
    task_data: schemas.CloudAgentTaskCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[models.User, Depends(get_current_user)],
) -> models.CloudAgentTask:
    """
    Crear una nueva tarea y delegarla al agente en la nube.

    El agente procesará la tarea de forma asíncrona según su prioridad.
    """
    _check_cloud_agent_enabled()
    
    task = cloud_agent.create_task(
        db=db,
        task_type=task_data.task_type,
        title=task_data.title,
        description=task_data.description,
        input_data=task_data.input_data,
        priority=task_data.priority,
        max_retries=task_data.max_retries,
        created_by_id=current_user.id,
    )
    
    return task


@router.get(
    "/tasks",
    response_model=schemas.CloudAgentTaskListResponse,
    summary="Listar tareas delegadas",
)
async def list_tasks(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[models.User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: models.CloudAgentTaskStatus | None = None,
    task_type: models.CloudAgentTaskType | None = None,
) -> schemas.CloudAgentTaskListResponse:
    """
    Listar tareas delegadas con filtros opcionales.

    Los usuarios pueden ver solo sus propias tareas, excepto los administradores
    que pueden ver todas las tareas.
    """
    _check_cloud_agent_enabled()
    
    # Los usuarios normales solo ven sus propias tareas
    created_by_id = None if current_user.is_admin else current_user.id
    
    skip = (page - 1) * size
    tasks, total = cloud_agent.list_tasks(
        db=db,
        skip=skip,
        limit=size,
        status=status,
        task_type=task_type,
        created_by_id=created_by_id,
    )
    
    # Parsear JSON en output_data e input_data
    for task in tasks:
        if task.output_data:
            try:
                task.output_data = json.loads(task.output_data)
            except (json.JSONDecodeError, TypeError):
                task.output_data = None
        if task.input_data:
            try:
                task.input_data = json.loads(task.input_data)
            except (json.JSONDecodeError, TypeError):
                task.input_data = None
    
    pages = math.ceil(total / size) if total > 0 else 1
    has_next = page < pages
    
    return schemas.CloudAgentTaskListResponse(
        items=tasks,
        total=total,
        page=page,
        size=size,
        pages=pages,
        has_next=has_next,
    )


@router.get(
    "/tasks/{task_id}",
    response_model=schemas.CloudAgentTaskResponse,
    summary="Obtener detalles de una tarea",
)
async def get_task(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[models.User, Depends(get_current_user)],
) -> models.CloudAgentTask:
    """
    Obtener los detalles completos de una tarea específica.
    """
    _check_cloud_agent_enabled()
    
    task = cloud_agent.get_task(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarea {task_id} no encontrada"
        )
    
    # Los usuarios normales solo pueden ver sus propias tareas
    if not current_user.is_admin and task.created_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para ver esta tarea"
        )
    
    # Parsear JSON en output_data e input_data
    if task.output_data:
        try:
            task.output_data = json.loads(task.output_data)
        except (json.JSONDecodeError, TypeError):
            task.output_data = None
    if task.input_data:
        try:
            task.input_data = json.loads(task.input_data)
        except (json.JSONDecodeError, TypeError):
            task.input_data = None
    
    return task


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancelar una tarea delegada",
)
async def cancel_task(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[models.User, Depends(get_current_user)],
) -> None:
    """
    Cancelar una tarea que está pendiente o en progreso.

    Las tareas ya completadas, fallidas o canceladas no se pueden cancelar.
    """
    _check_cloud_agent_enabled()
    
    task = cloud_agent.get_task(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarea {task_id} no encontrada"
        )
    
    # Los usuarios normales solo pueden cancelar sus propias tareas
    if not current_user.is_admin and task.created_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para cancelar esta tarea"
        )
    
    cancelled_task = cloud_agent.cancel_task(db, task_id)
    if not cancelled_task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La tarea {task_id} no se puede cancelar en su estado actual"
        )


@router.get(
    "/stats",
    response_model=schemas.CloudAgentTaskStats,
    summary="Obtener estadísticas de tareas",
)
async def get_stats(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[models.User, Depends(get_current_user)],
) -> schemas.CloudAgentTaskStats:
    """
    Obtener estadísticas agregadas de todas las tareas delegadas.

    Solo accesible para administradores.
    """
    _check_cloud_agent_enabled()
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden ver estadísticas globales"
        )
    
    stats = cloud_agent.get_task_stats(db)
    return schemas.CloudAgentTaskStats(**stats)


@router.post(
    "/tasks/retry-failed",
    response_model=list[schemas.CloudAgentTaskResponse],
    summary="Reintentar tareas fallidas",
)
async def retry_failed_tasks(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[models.User, Depends(get_current_user)],
    max_tasks: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[models.CloudAgentTask]:
    """
    Reintentar tareas fallidas que no han excedido el máximo de reintentos.

    Solo accesible para administradores.
    """
    _check_cloud_agent_enabled()
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden reintentar tareas"
        )
    
    retried_tasks = cloud_agent.retry_failed_tasks(db, max_tasks=max_tasks)
    return retried_tasks
