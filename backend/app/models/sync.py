from __future__ import annotations
import enum
import json
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base
from backend.app.models.users import User
from backend.app.models.stores import Store

if TYPE_CHECKING:
    pass


class SyncStatus(str, enum.Enum):
    """Estados posibles de una sesión de sincronización."""

    SUCCESS = "exitoso"
    FAILED = "fallido"


class SyncMode(str, enum.Enum):
    """Modo en el que se dispara la sincronización."""

    AUTOMATIC = "automatico"
    MANUAL = "manual"


class SyncOutboxStatus(str, enum.Enum):
    """Estados posibles de un evento en la cola de sincronización."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class SyncOutboxPriority(str, enum.Enum):
    """Prioridad de procesamiento para eventos híbridos."""

    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class SyncQueueStatus(str, enum.Enum):
    """Estados de la cola de sincronización (Legacy/Compatibilidad)."""
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class SyncSession(Base):
    __tablename__ = "sync_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int | None] = mapped_column(
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    mode: Mapped[SyncMode] = mapped_column(
        Enum(SyncMode, name="sync_mode"), nullable=False)
    status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus, name="sync_status"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )

    store: Mapped[Store | None] = relationship(
        "Store", back_populates="sync_sessions")
    triggered_by: Mapped[User | None] = relationship(
        "User", back_populates="sync_sessions")


class SyncOutbox(Base):
    __tablename__ = "sync_outbox"
    __table_args__ = (UniqueConstraint(
        "entity_type", "entity_id", name="uq_outbox_entity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(
        String(120), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(80), nullable=False)
    operation: Mapped[str] = mapped_column(String(40), nullable=False)
    _payload: Mapped[str] = mapped_column("payload", Text, nullable=False)
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    status: Mapped[SyncOutboxStatus] = mapped_column(
        Enum(SyncOutboxStatus, name="sync_outbox_status"),
        nullable=False,
        default=SyncOutboxStatus.PENDING,
    )
    priority: Mapped[SyncOutboxPriority] = mapped_column(
        Enum(SyncOutboxPriority, name="sync_outbox_priority"),
        nullable=False,
        default=SyncOutboxPriority.NORMAL,
    )
    error_message: Mapped[str | None] = mapped_column(
        String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    conflict_flag: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True)
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, index=True)

    def _get_payload(self) -> dict[str, Any]:
        raw = self._payload
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:  # pragma: no cover - datos corruptos
                return {}
        if raw is None:
            return {}
        try:
            return dict(raw)
        except TypeError:  # pragma: no cover - tolerar tipos no previstos
            return {}

    def _set_payload(self, value: dict[str, Any] | str | None) -> None:
        if value is None:
            self._payload = json.dumps({}, ensure_ascii=False)
            return
        if isinstance(value, str):
            self._payload = value
            return
        self._payload = json.dumps(value, ensure_ascii=False, default=str)

    payload = property(_get_payload, _set_payload)
