"""Modelos para delegación de tareas al agente en la nube."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database import Base

if TYPE_CHECKING:
    from .users import User


class CloudAgentTaskStatus(str, enum.Enum):
    """Estados posibles de una tarea delegada al agente en la nube."""

    PENDING = "pending"  # Tarea creada, esperando procesamiento
    IN_PROGRESS = "in_progress"  # El agente está trabajando en la tarea
    COMPLETED = "completed"  # Tarea completada exitosamente
    FAILED = "failed"  # Tarea falló durante el procesamiento
    CANCELLED = "cancelled"  # Tarea cancelada por el usuario


class CloudAgentTaskType(str, enum.Enum):
    """Tipos de tareas que se pueden delegar al agente en la nube."""

    SYNC_DATA = "sync_data"  # Sincronización de datos con la nube
    GENERATE_REPORT = "generate_report"  # Generación de reportes
    PROCESS_BATCH = "process_batch"  # Procesamiento por lotes
    ANALYZE_DATA = "analyze_data"  # Análisis de datos
    BACKUP_DATA = "backup_data"  # Respaldo de datos
    CUSTOM = "custom"  # Tarea personalizada


class CloudAgentTask(Base):
    """Representa una tarea delegada al agente en la nube."""

    __tablename__ = "cloud_agent_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(
        Enum(CloudAgentTaskType),
        nullable=False,
        index=True,
        comment="Tipo de tarea a ejecutar",
    )
    status = Column(
        Enum(CloudAgentTaskStatus),
        nullable=False,
        default=CloudAgentTaskStatus.PENDING,
        index=True,
        comment="Estado actual de la tarea",
    )
    title = Column(
        String(200),
        nullable=False,
        comment="Título descriptivo de la tarea",
    )
    description = Column(
        Text,
        nullable=True,
        comment="Descripción detallada de la tarea",
    )
    input_data = Column(
        Text,
        nullable=True,
        comment="Datos de entrada en formato JSON",
    )
    output_data = Column(
        Text,
        nullable=True,
        comment="Resultado de la tarea en formato JSON",
    )
    error_message = Column(
        Text,
        nullable=True,
        comment="Mensaje de error si la tarea falló",
    )
    created_by_id = Column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Usuario que creó la tarea",
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Fecha y hora de creación",
    )
    started_at = Column(
        DateTime,
        nullable=True,
        comment="Fecha y hora de inicio de procesamiento",
    )
    completed_at = Column(
        DateTime,
        nullable=True,
        comment="Fecha y hora de completado",
    )
    priority = Column(
        Integer,
        nullable=False,
        default=5,
        comment="Prioridad de la tarea (1=alta, 10=baja)",
    )
    retry_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Número de reintentos realizados",
    )
    max_retries = Column(
        Integer,
        nullable=False,
        default=3,
        comment="Número máximo de reintentos permitidos",
    )

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])

    def __repr__(self) -> str:
        return f"<CloudAgentTask(id={self.id}, type={self.task_type}, status={self.status})>"
