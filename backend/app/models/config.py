from __future__ import annotations
import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base

if TYPE_CHECKING:
    from .users import User


class BackupMode(str, enum.Enum):
    """Origen del respaldo generado."""

    AUTOMATIC = "automatico"
    MANUAL = "manual"


class BackupComponent(str, enum.Enum):
    """Componentes disponibles dentro de un respaldo corporativo."""

    DATABASE = "database"
    CONFIGURATION = "configuration"
    CRITICAL_FILES = "critical_files"


class ConfigRate(Base):
    __tablename__ = "config_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(
        String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class ConfigXmlTemplate(Base):
    __tablename__ = "config_xml_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(
        String(80), unique=True, index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    namespace: Mapped[str | None] = mapped_column(String(255), nullable=True)
    schema_location: Mapped[str | None] = mapped_column(
        String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class ConfigParameter(Base):
    __tablename__ = "config_parameters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(
        String(120), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_type: Mapped[str] = mapped_column(String(20), nullable=False)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_json: Mapped[dict[str, Any] |
                       None] = mapped_column(JSON, nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class BackupJob(Base):
    __tablename__ = "backup_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    archive_path: Mapped[str] = mapped_column(String(512), nullable=False)
    pdf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sql_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    json_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    config_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_path: Mapped[str | None] = mapped_column(
        String(512), nullable=True)
    critical_directory: Mapped[str | None] = mapped_column(
        String(512), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    total_size_bytes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    mode: Mapped[BackupMode] = mapped_column(
        Enum(BackupMode, name="backup_mode"), nullable=False
    )
    components: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    created_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario"), nullable=True, index=True)
    triggered_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="completed")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    triggered_by: Mapped[User | None] = relationship(
        "User", back_populates="backup_jobs", foreign_keys="BackupJob.triggered_by_id"
    )
