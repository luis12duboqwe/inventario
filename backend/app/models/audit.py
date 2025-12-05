from __future__ import annotations
import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional, Any
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base
from backend.app.models.users import User

if TYPE_CHECKING:
    pass


class SystemLogLevel(str, enum.Enum):
    """Niveles de severidad admitidos en la bitácora general."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class FeedbackCategory(str, enum.Enum):
    INCIDENTE = "incidente"
    MEJORA = "mejora"
    USABILIDAD = "usabilidad"
    RENDIMIENTO = "rendimiento"
    CONSULTA = "consulta"


class FeedbackPriority(str, enum.Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class FeedbackStatus(str, enum.Enum):
    ABIERTO = "abierto"
    EN_PROGRESO = "en_progreso"
    RESUELTO = "resuelto"
    DESCARTADO = "descartado"


class SupportFeedback(Base):
    """Sugerencias, incidencias y mejoras reportadas por usuarios corporativos."""

    __tablename__ = "support_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tracking_id: Mapped[str] = mapped_column(
        String(36), default=lambda: str(uuid4()), unique=True, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    contact: Mapped[str | None] = mapped_column(String(180), nullable=True)
    module: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    category: Mapped[FeedbackCategory] = mapped_column(
        Enum(FeedbackCategory, name="feedback_category"), nullable=False
    )
    priority: Mapped[FeedbackPriority] = mapped_column(
        Enum(FeedbackPriority, name="feedback_priority"), nullable=False, default=FeedbackPriority.MEDIA
    )
    status: Mapped[FeedbackStatus] = mapped_column(
        Enum(FeedbackStatus, name="feedback_status"), nullable=False, default=FeedbackStatus.ABIERTO
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False)
    usage_context: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped[User | None] = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(80), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)

    performed_by: Mapped[User | None] = relationship(
        "User", back_populates="logs")
    system_log: Mapped[Optional["SystemLog"]] = relationship(
        "SystemLog", back_populates="audit_log", uselist=False
    )

    @property
    def module(self) -> str | None:
        """Nombre del módulo asociado al evento de auditoría."""

        if self.system_log is None:
            return None
        return self.system_log.modulo


class AuditAlertAcknowledgement(Base):
    __tablename__ = "audit_alert_acknowledgements"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id",
                         name="uq_audit_ack_entity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(
        String(80), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(
        String(80), nullable=False, index=True)
    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    acknowledged_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    acknowledged_by: Mapped[User | None] = relationship(
        "User", back_populates="audit_acknowledgements"
    )


class AuditUI(Base):
    """Eventos de interacción registrados desde la interfaz de usuario."""

    __tablename__ = "audit_ui"

    # // [PACK32-33-BE] Retención sugerida: conservar 180 días y depurar con job programado.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(
        String(120), nullable=True, index=True)
    module: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    action: Mapped[str] = mapped_column(
        String(120), nullable=False, index=True)
    entity_id: Mapped[str | None] = mapped_column(
        String(120), nullable=True, index=True)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class SystemLog(Base):
    __tablename__ = "logs_sistema"

    id: Mapped[int] = mapped_column(
        "id_log", Integer, primary_key=True, index=True)
    usuario: Mapped[str | None] = mapped_column(
        String(120), nullable=True, index=True)
    modulo: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    accion: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
    nivel: Mapped[SystemLogLevel] = mapped_column(
        Enum(SystemLogLevel, name="system_log_level"), nullable=False, index=True
    )
    ip_origen: Mapped[str | None] = mapped_column(String(45), nullable=True)
    audit_log_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("audit_logs.id", ondelete="SET NULL"), nullable=True, unique=True
    )

    audit_log: Mapped[AuditLog | None] = relationship(
        "AuditLog", back_populates="system_log")


class SystemError(Base):
    __tablename__ = "errores_sistema"

    id: Mapped[int] = mapped_column(
        "id_error", Integer, primary_key=True, index=True)
    mensaje: Mapped[str] = mapped_column(String(255), nullable=False)
    stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)
    modulo: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
    usuario: Mapped[str | None] = mapped_column(
        String(120), nullable=True, index=True)
