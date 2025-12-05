"""Esquemas Pydantic para delegación de tareas al agente en la nube."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict

from ..models.cloud_agent import CloudAgentTaskStatus, CloudAgentTaskType


class CloudAgentTaskBase(BaseModel):
    """Esquema base para tareas del agente en la nube."""

    task_type: CloudAgentTaskType = Field(
        ...,
        description="Tipo de tarea a ejecutar"
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Título descriptivo de la tarea"
    )
    description: str | None = Field(
        default=None,
        description="Descripción detallada de la tarea"
    )
    input_data: dict[str, Any] | None = Field(
        default=None,
        description="Datos de entrada para la tarea"
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Prioridad de la tarea (1=alta, 10=baja)"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Número máximo de reintentos permitidos"
    )


class CloudAgentTaskCreate(CloudAgentTaskBase):
    """Esquema para crear una nueva tarea del agente en la nube."""
    pass


class CloudAgentTaskUpdate(BaseModel):
    """Esquema para actualizar una tarea del agente en la nube."""

    status: CloudAgentTaskStatus | None = Field(
        default=None,
        description="Nuevo estado de la tarea"
    )
    output_data: dict[str, Any] | None = Field(
        default=None,
        description="Resultado de la tarea"
    )
    error_message: str | None = Field(
        default=None,
        description="Mensaje de error si la tarea falló"
    )


class CloudAgentTaskResponse(CloudAgentTaskBase):
    """Esquema de respuesta para una tarea del agente en la nube."""

    id: int
    status: CloudAgentTaskStatus
    output_data: dict[str, Any] | None = None
    error_message: str | None = None
    created_by_id: int | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class CloudAgentTaskListResponse(BaseModel):
    """Esquema de respuesta para listar tareas con paginación."""

    items: list[CloudAgentTaskResponse]
    total: int
    page: int = 1
    size: int = 20
    pages: int
    has_next: bool


class CloudAgentTaskStats(BaseModel):
    """Estadísticas de tareas del agente en la nube."""

    total_tasks: int = 0
    pending_tasks: int = 0
    in_progress_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    avg_completion_time_seconds: float | None = None
