"""Modelos ORM del dominio de Softmobile Central."""
from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class MovementType(str, enum.Enum):
    """Tipos permitidos de movimientos de inventario."""

    IN = "entrada"
    OUT = "salida"
    ADJUST = "ajuste"


class SyncStatus(str, enum.Enum):
    """Estados posibles de una sesión de sincronización."""

    SUCCESS = "exitoso"
    FAILED = "fallido"


class SyncMode(str, enum.Enum):
    """Modo en el que se dispara la sincronización."""

    AUTOMATIC = "automatico"
    MANUAL = "manual"


class BackupMode(str, enum.Enum):
    """Origen del respaldo generado."""

    AUTOMATIC = "automatico"
    MANUAL = "manual"


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")

    devices: Mapped[list["Device"]] = relationship(
        "Device", back_populates="store", cascade="all, delete-orphan"
    )
    movements: Mapped[list["InventoryMovement"]] = relationship(
        "InventoryMovement",
        back_populates="store",
        cascade="all, delete-orphan",
    )
    sync_sessions: Mapped[list["SyncSession"]] = relationship(
        "SyncSession", back_populates="store", cascade="all, delete-orphan"
    )


class CommercialState(str, enum.Enum):
    """Clasificación comercial del dispositivo en catálogo pro."""

    NUEVO = "nuevo"
    A = "A"
    B = "B"
    C = "C"


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("store_id", "sku", name="uq_devices_store_sku"),
        UniqueConstraint("imei", name="uq_devices_imei"),
        UniqueConstraint("serial", name="uq_devices_serial"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sku: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    imei: Mapped[str | None] = mapped_column(String(18), nullable=True, unique=True, index=True)
    serial: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True, index=True)
    marca: Mapped[str | None] = mapped_column(String(80), nullable=True)
    modelo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    color: Mapped[str | None] = mapped_column(String(60), nullable=True)
    capacidad_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estado_comercial: Mapped[CommercialState] = mapped_column(
        Enum(CommercialState, name="estado_comercial"), nullable=False, default=CommercialState.NUEVO
    )
    proveedor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    margen_porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0"))
    garantia_meses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lote: Mapped[str | None] = mapped_column(String(80), nullable=True)
    fecha_compra: Mapped[date | None] = mapped_column(Date, nullable=True)

    store: Mapped[Store] = relationship("Store", back_populates="devices")
    movements: Mapped[list["InventoryMovement"]] = relationship(
        "InventoryMovement",
        back_populates="device",
        cascade="all, delete-orphan",
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    users: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan"
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="user", cascade="all, delete-orphan"
    )
    movements: Mapped[list["InventoryMovement"]] = relationship("InventoryMovement", back_populates="performed_by")
    sync_sessions: Mapped[list["SyncSession"]] = relationship("SyncSession", back_populates="triggered_by")
    logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="performed_by")
    backup_jobs: Mapped[list["BackupJob"]] = relationship("BackupJob", back_populates="triggered_by")


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), index=True)

    user: Mapped[User] = relationship("User", back_populates="roles")
    role: Mapped[Role] = relationship("Role", back_populates="users")


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    movement_type: Mapped[MovementType] = mapped_column(Enum(MovementType, name="movement_type"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    performed_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    store: Mapped[Store] = relationship("Store", back_populates="movements")
    device: Mapped[Device] = relationship("Device", back_populates="movements")
    performed_by: Mapped[User | None] = relationship("User", back_populates="movements")


class SyncSession(Base):
    __tablename__ = "sync_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("stores.id", ondelete="SET NULL"), nullable=True, index=True
    )
    mode: Mapped[SyncMode] = mapped_column(Enum(SyncMode, name="sync_mode"), nullable=False)
    status: Mapped[SyncStatus] = mapped_column(Enum(SyncStatus, name="sync_status"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    store: Mapped[Store | None] = relationship("Store", back_populates="sync_sessions")
    triggered_by: Mapped[User | None] = relationship("User", back_populates="sync_sessions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(80), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    performed_by: Mapped[User | None] = relationship("User", back_populates="logs")


class BackupJob(Base):
    __tablename__ = "backup_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mode: Mapped[BackupMode] = mapped_column(Enum(BackupMode, name="backup_mode"), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    pdf_path: Mapped[str] = mapped_column(String(255), nullable=False)
    archive_path: Mapped[str] = mapped_column(String(255), nullable=False)
    total_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    triggered_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    triggered_by: Mapped[User | None] = relationship("User", back_populates="backup_jobs")


__all__ = [
    "AuditLog",
    "BackupJob",
    "BackupMode",
    "Device",
    "InventoryMovement",
    "MovementType",
    "Role",
    "Store",
    "SyncMode",
    "SyncSession",
    "SyncStatus",
    "User",
    "UserRole",
]
