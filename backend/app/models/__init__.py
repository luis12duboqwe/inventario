"""Modelos ORM del dominio de Softmobile Central."""
from __future__ import annotations

import enum
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

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
    inventory_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )

    devices: Mapped[list["Device"]] = relationship(
        "Device", back_populates="store", cascade="all, delete-orphan"
    )
    movements: Mapped[list["InventoryMovement"]] = relationship(
        "InventoryMovement",
        back_populates="store",
        cascade="all, delete-orphan",
        foreign_keys="InventoryMovement.store_id",
    )
    sync_sessions: Mapped[list["SyncSession"]] = relationship(
        "SyncSession", back_populates="store", cascade="all, delete-orphan"
    )
    supplier_batches: Mapped[list["SupplierBatch"]] = relationship(
        "SupplierBatch", back_populates="store", cascade="all, delete-orphan"
    )


class CommercialState(str, enum.Enum):
    """Clasificación comercial del dispositivo en catálogo pro."""

    NUEVO = "nuevo"
    A = "A"
    B = "B"
    C = "C"


class TransferStatus(str, enum.Enum):
    """Estados posibles de una orden de transferencia."""

    SOLICITADA = "SOLICITADA"
    EN_TRANSITO = "EN_TRANSITO"
    RECIBIDA = "RECIBIDA"
    CANCELADA = "CANCELADA"


class PurchaseStatus(str, enum.Enum):
    """Estados de avance para las órdenes de compra."""

    PENDIENTE = "PENDIENTE"
    PARCIAL = "PARCIAL"
    COMPLETADA = "COMPLETADA"
    CANCELADA = "CANCELADA"


class RepairStatus(str, enum.Enum):
    """Estados de una orden de reparación."""

    PENDIENTE = "PENDIENTE"
    EN_PROCESO = "EN_PROCESO"
    LISTO = "LISTO"
    ENTREGADO = "ENTREGADO"


class CashSessionStatus(str, enum.Enum):
    """Ciclo de vida de un arqueo de caja POS."""

    ABIERTO = "ABIERTO"
    CERRADO = "CERRADO"


class PaymentMethod(str, enum.Enum):
    """Formas de pago soportadas en las ventas."""

    EFECTIVO = "EFECTIVO"
    TARJETA = "TARJETA"
    CREDITO = "CREDITO"
    TRANSFERENCIA = "TRANSFERENCIA"
    OTRO = "OTRO"


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
    categoria: Mapped[str | None] = mapped_column(String(80), nullable=True)
    condicion: Mapped[str | None] = mapped_column(String(60), nullable=True)
    color: Mapped[str | None] = mapped_column(String(60), nullable=True)
    capacidad_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capacidad: Mapped[str | None] = mapped_column(String(80), nullable=True)
    estado_comercial: Mapped[CommercialState] = mapped_column(
        Enum(CommercialState, name="estado_comercial"), nullable=False, default=CommercialState.NUEVO
    )
    estado: Mapped[str] = mapped_column(String(40), nullable=False, default="disponible")
    proveedor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    margen_porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0"))
    garantia_meses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lote: Mapped[str | None] = mapped_column(String(80), nullable=True)
    fecha_compra: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_ingreso: Mapped[date | None] = mapped_column(Date, nullable=True)
    ubicacion: Mapped[str | None] = mapped_column(String(120), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    imagen_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    store: Mapped[Store] = relationship("Store", back_populates="devices")
    movements: Mapped[list["InventoryMovement"]] = relationship(
        "InventoryMovement",
        back_populates="device",
        cascade="all, delete-orphan",
    )
    identifier: Mapped["DeviceIdentifier | None"] = relationship(
        "DeviceIdentifier",
        back_populates="device",
        cascade="all, delete-orphan",
        uselist=False,
    )

    @property
    def costo_compra(self) -> Decimal:
        """Alias semántico de ``costo_unitario`` para reportes corporativos."""

        return self.costo_unitario

    @costo_compra.setter
    def costo_compra(self, value: Decimal) -> None:
        self.costo_unitario = value

    @property
    def precio_venta(self) -> Decimal:
        """Alias semántico de ``unit_price`` para el catálogo de productos."""

        return self.unit_price

    @precio_venta.setter
    def precio_venta(self, value: Decimal) -> None:
        self.unit_price = value


class DeviceIdentifier(Base):
    __tablename__ = "device_identifiers"
    __table_args__ = (
        UniqueConstraint("producto_id", name="uq_device_identifiers_producto"),
        UniqueConstraint("imei_1", name="uq_device_identifiers_imei_1"),
        UniqueConstraint("imei_2", name="uq_device_identifiers_imei_2"),
        UniqueConstraint("numero_serie", name="uq_device_identifiers_numero_serie"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    producto_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    imei_1: Mapped[str | None] = mapped_column(String(18), nullable=True)
    imei_2: Mapped[str | None] = mapped_column(String(18), nullable=True)
    numero_serie: Mapped[str | None] = mapped_column(String(120), nullable=True)
    estado_tecnico: Mapped[str | None] = mapped_column(String(60), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    device: Mapped[Device] = relationship("Device", back_populates="identifier")


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
    totp_secret: Mapped[UserTOTPSecret | None] = relationship(
        "UserTOTPSecret", back_populates="user", uselist=False
    )
    active_sessions: Mapped[list["ActiveSession"]] = relationship(
        "ActiveSession",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="ActiveSession.user_id",
    )
    audit_acknowledgements: Mapped[list["AuditAlertAcknowledgement"]] = relationship(
        "AuditAlertAcknowledgement",
        back_populates="acknowledged_by",
        cascade="all, delete-orphan",
    )


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
    store_id: Mapped[int] = mapped_column(
        "tienda_destino_id",
        Integer,
        ForeignKey("stores.id", ondelete="CASCADE"),
        index=True,
    )
    source_store_id: Mapped[int | None] = mapped_column(
        "tienda_origen_id",
        Integer,
        ForeignKey("stores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    device_id: Mapped[int] = mapped_column(
        "producto_id",
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        index=True,
    )
    movement_type: Mapped[MovementType] = mapped_column(
        "tipo_movimiento", Enum(MovementType, name="movement_type"), nullable=False
    )
    quantity: Mapped[int] = mapped_column("cantidad", Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column("comentario", String(255), nullable=True)
    unit_cost: Mapped[Decimal | None] = mapped_column(
        "costo_unitario", Numeric(12, 2), nullable=True
    )
    performed_by_id: Mapped[int | None] = mapped_column(
        "usuario_id",
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        "fecha", DateTime(timezone=True), default=datetime.utcnow
    )

    store: Mapped[Store] = relationship(
        "Store",
        back_populates="movements",
        foreign_keys=[store_id],
    )
    source_store: Mapped[Store | None] = relationship(
        "Store",
        foreign_keys=[source_store_id],
    )
    device: Mapped[Device] = relationship("Device", back_populates="movements")
    performed_by: Mapped[User | None] = relationship("User", back_populates="movements")

    @property
    def usuario(self) -> str | None:
        """Nombre descriptivo del usuario que registró el movimiento."""

        if self.performed_by is None:
            return None
        if self.performed_by.full_name:
            return self.performed_by.full_name
        return self.performed_by.username

    @property
    def tienda_origen(self) -> str | None:
        """Nombre de la sucursal de origen, si aplica."""

        if self.source_store is None:
            return None
        return self.source_store.name

    @property
    def tienda_destino(self) -> str | None:
        """Nombre de la sucursal destino."""

        if self.store is None:
            return None
        return self.store.name


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


class AuditAlertAcknowledgement(Base):
    __tablename__ = "audit_alert_acknowledgements"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", name="uq_audit_ack_entity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    acknowledged_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    acknowledged_by: Mapped[User | None] = relationship(
        "User", back_populates="audit_acknowledgements"
    )


class BackupJob(Base):
    __tablename__ = "backup_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mode: Mapped[BackupMode] = mapped_column(Enum(BackupMode, name="backup_mode"), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    pdf_path: Mapped[str] = mapped_column(String(255), nullable=False)
    archive_path: Mapped[str] = mapped_column(String(255), nullable=False)
    total_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    triggered_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    triggered_by: Mapped[User | None] = relationship("User", back_populates="backup_jobs")


class TransferOrder(Base):
    __tablename__ = "transfer_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    origin_store_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    destination_store_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[TransferStatus] = mapped_column(
        Enum(TransferStatus, name="transfer_status"),
        nullable=False,
        default=TransferStatus.SOLICITADA,
    )
    requested_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    dispatched_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    received_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    cancelled_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    origin_store: Mapped[Store] = relationship(
        "Store", foreign_keys=[origin_store_id], backref="transfer_orders_out"
    )
    destination_store: Mapped[Store] = relationship(
        "Store", foreign_keys=[destination_store_id], backref="transfer_orders_in"
    )
    requested_by: Mapped[User | None] = relationship("User", foreign_keys=[requested_by_id])
    dispatched_by: Mapped[User | None] = relationship("User", foreign_keys=[dispatched_by_id])
    received_by: Mapped[User | None] = relationship("User", foreign_keys=[received_by_id])
    cancelled_by: Mapped[User | None] = relationship("User", foreign_keys=[cancelled_by_id])
    items: Mapped[list["TransferOrderItem"]] = relationship(
        "TransferOrderItem", back_populates="transfer_order", cascade="all, delete-orphan"
    )


class TransferOrderItem(Base):
    __tablename__ = "transfer_order_items"
    __table_args__ = (
        UniqueConstraint("transfer_order_id", "device_id", name="uq_transfer_item_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    transfer_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("transfer_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    transfer_order: Mapped[TransferOrder] = relationship(
        "TransferOrder", back_populates="items"
    )
    device: Mapped[Device] = relationship("Device")


class RecurringOrderType(str, enum.Enum):
    """Tipos disponibles para plantillas recurrentes."""

    PURCHASE = "purchase"
    TRANSFER = "transfer"


class RecurringOrder(Base):
    __tablename__ = "recurring_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    order_type: Mapped[RecurringOrderType] = mapped_column(
        Enum(RecurringOrderType, name="recurring_order_type"),
        nullable=False,
    )
    store_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("stores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    last_used_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    store: Mapped[Store | None] = relationship("Store")
    created_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[created_by_id], backref="recurring_orders_created"
    )
    last_used_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[last_used_by_id], backref="recurring_orders_used"
    )


class StoreMembership(Base):
    __tablename__ = "store_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "store_id", name="uq_membership_user_store"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    store_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    can_create_transfer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_receive_transfer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    user: Mapped[User] = relationship("User", backref="store_memberships")
    store: Mapped[Store] = relationship("Store", backref="memberships")


class Customer(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column("id_cliente", Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        "nombre", String(120), nullable=False, unique=True, index=True
    )
    contact_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email: Mapped[str | None] = mapped_column(
        "correo", String(120), nullable=True, unique=True, index=True
    )
    phone: Mapped[str] = mapped_column(
        "telefono", String(40), nullable=False, index=True
    )
    address: Mapped[str | None] = mapped_column("direccion", String(255), nullable=True)
    customer_type: Mapped[str] = mapped_column(
        "tipo", String(30), nullable=False, default="minorista", index=True
    )
    status: Mapped[str] = mapped_column(
        "estado", String(20), nullable=False, default="activo", index=True
    )
    credit_limit: Mapped[Decimal] = mapped_column(
        "limite_credito", Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    outstanding_debt: Mapped[Decimal] = mapped_column(
        "saldo", Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    notes: Mapped[str | None] = mapped_column("notas", Text, nullable=True)
    history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    last_interaction_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    repair_orders: Mapped[list["RepairOrder"]] = relationship(
        "RepairOrder", back_populates="customer"
    )
    sales: Mapped[list["Sale"]] = relationship("Sale", back_populates="customer")


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    contact_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    outstanding_debt: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    batches: Mapped[list["SupplierBatch"]] = relationship(
        "SupplierBatch", back_populates="supplier", cascade="all, delete-orphan"
    )


class SupplierBatch(Base):
    __tablename__ = "supplier_batches"
    __table_args__ = (
        UniqueConstraint("supplier_id", "batch_code", name="uq_supplier_batch_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    supplier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    store_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("stores.id", ondelete="SET NULL"), nullable=True, index=True
    )
    device_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True
    )
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    batch_code: Mapped[str] = mapped_column(String(80), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="batches")
    store: Mapped[Store | None] = relationship("Store", back_populates="supplier_batches")
    device: Mapped[Device | None] = relationship("Device")


class Proveedor(Base):
    """Catálogo simplificado de proveedores corporativos."""

    __tablename__ = "proveedores"

    id_proveedor: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
    telefono: Mapped[str | None] = mapped_column(String(40), nullable=True)
    correo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tipo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    estado: Mapped[str] = mapped_column(String(40), nullable=False, default="activo")
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    compras: Mapped[list["Compra"]] = relationship(
        "Compra", back_populates="proveedor", cascade="all, delete-orphan"
    )


class Compra(Base):
    """Encabezado de compras directas registradas en el módulo clásico."""

    __tablename__ = "compras"

    id_compra: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    proveedor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("proveedores.id_proveedor", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    usuario_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    impuesto: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    forma_pago: Mapped[str] = mapped_column(String(60), nullable=False)
    estado: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDIENTE")

    proveedor: Mapped[Proveedor] = relationship("Proveedor", back_populates="compras")
    usuario: Mapped["User"] = relationship("User")
    detalles: Mapped[list["DetalleCompra"]] = relationship(
        "DetalleCompra", back_populates="compra", cascade="all, delete-orphan"
    )


class DetalleCompra(Base):
    """Detalle de productos asociados a una compra simplificada."""

    __tablename__ = "detalle_compras"

    id_detalle: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    compra_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("compras.id_compra", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    producto_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    costo_unitario: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )

    compra: Mapped[Compra] = relationship("Compra", back_populates="detalles")
    producto: Mapped[Device] = relationship("Device")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    supplier: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[PurchaseStatus] = mapped_column(
        Enum(PurchaseStatus, name="purchase_status"),
        nullable=False,
        default=PurchaseStatus.PENDIENTE,
    )
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    store: Mapped[Store] = relationship("Store")
    created_by: Mapped[User | None] = relationship("User")
    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        "PurchaseOrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    returns: Mapped[list["PurchaseReturn"]] = relationship(
        "PurchaseReturn", back_populates="order", cascade="all, delete-orphan"
    )


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    __table_args__ = (
        UniqueConstraint("purchase_order_id", "device_id", name="uq_purchase_item_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))

    order: Mapped[PurchaseOrder] = relationship("PurchaseOrder", back_populates="items")
    device: Mapped[Device] = relationship("Device")


class PurchaseReturn(Base):
    __tablename__ = "purchase_returns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    processed_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    order: Mapped[PurchaseOrder] = relationship("PurchaseOrder", back_populates="returns")
    device: Mapped[Device] = relationship("Device")
    processed_by: Mapped[User | None] = relationship("User")


class Sale(Base):
    __tablename__ = "ventas"

    id: Mapped[int] = mapped_column("id_venta", Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_id: Mapped[int | None] = mapped_column(
        "cliente_id",
        Integer,
        ForeignKey("clientes.id_cliente", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        "forma_pago",
        Enum(PaymentMethod, name="payment_method"),
        nullable=False,
        default=PaymentMethod.EFECTIVO,
    )
    discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0")
    )
    subtotal_amount: Mapped[Decimal] = mapped_column(
        "subtotal", Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        "impuesto", Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    total_amount: Mapped[Decimal] = mapped_column(
        "total", Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    status: Mapped[str] = mapped_column(
        "estado", String(30), nullable=False, default="COMPLETADA"
    )
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        "fecha", DateTime(timezone=True), default=datetime.utcnow
    )
    performed_by_id: Mapped[int | None] = mapped_column(
        "usuario_id",
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cash_session_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("cash_register_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    store: Mapped[Store] = relationship("Store")
    performed_by: Mapped[User | None] = relationship("User")
    customer: Mapped[Customer | None] = relationship("Customer", back_populates="sales")
    cash_session: Mapped[CashRegisterSession | None] = relationship(
        "CashRegisterSession", back_populates="sales"
    )
    items: Mapped[list["SaleItem"]] = relationship(
        "SaleItem", back_populates="sale", cascade="all, delete-orphan"
    )
    returns: Mapped[list["SaleReturn"]] = relationship(
        "SaleReturn", back_populates="sale", cascade="all, delete-orphan"
    )


class SaleItem(Base):
    __tablename__ = "detalle_ventas"

    id: Mapped[int] = mapped_column("id_detalle", Integer, primary_key=True, index=True)
    sale_id: Mapped[int] = mapped_column(
        "venta_id",
        Integer,
        ForeignKey("ventas.id_venta", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[int] = mapped_column(
        "producto_id",
        Integer,
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(
        "precio_unitario", Numeric(12, 2), nullable=False
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    total_line: Mapped[Decimal] = mapped_column(
        "subtotal", Numeric(12, 2), nullable=False
    )

    sale: Mapped[Sale] = relationship("Sale", back_populates="items")
    device: Mapped[Device] = relationship("Device")


class SaleReturn(Base):
    __tablename__ = "sale_returns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sale_id: Mapped[int] = mapped_column(
        "venta_id",
        Integer,
        ForeignKey("ventas.id_venta", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    processed_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    sale: Mapped[Sale] = relationship("Sale", back_populates="returns")
    device: Mapped[Device] = relationship("Device")
    processed_by: Mapped[User | None] = relationship("User")


class RepairOrder(Base):
    __tablename__ = "repair_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("clientes.id_cliente", ondelete="SET NULL"), nullable=True, index=True
    )
    customer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    technician_name: Mapped[str] = mapped_column(String(120), nullable=False)
    damage_type: Mapped[str] = mapped_column(String(120), nullable=False)
    device_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[RepairStatus] = mapped_column(
        Enum(RepairStatus, name="repair_status"),
        nullable=False,
        default=RepairStatus.PENDIENTE,
    )
    labor_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    parts_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    total_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    parts_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    inventory_adjusted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    store: Mapped[Store] = relationship("Store")
    customer: Mapped[Customer | None] = relationship("Customer", back_populates="repair_orders")
    parts: Mapped[list["RepairOrderPart"]] = relationship(
        "RepairOrderPart", back_populates="repair_order", cascade="all, delete-orphan"
    )


class RepairOrderPart(Base):
    __tablename__ = "repair_order_parts"
    __table_args__ = (
        UniqueConstraint("repair_order_id", "device_id", name="uq_repair_order_part"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    repair_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repair_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )

    repair_order: Mapped[RepairOrder] = relationship("RepairOrder", back_populates="parts")
    device: Mapped[Device] = relationship("Device")


class CashRegisterSession(Base):
    __tablename__ = "cash_register_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[CashSessionStatus] = mapped_column(
        Enum(CashSessionStatus, name="cash_session_status"),
        nullable=False,
        default=CashSessionStatus.ABIERTO,
    )
    opening_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    closing_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    expected_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    difference_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    payment_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    opened_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    closed_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    store: Mapped[Store] = relationship("Store")
    opened_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[opened_by_id], backref="cash_sessions_opened"
    )
    closed_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[closed_by_id], backref="cash_sessions_closed"
    )
    sales: Mapped[list[Sale]] = relationship("Sale", back_populates="cash_session")


class POSConfig(Base):
    __tablename__ = "pos_configs"

    store_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("stores.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0"))
    invoice_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    printer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    printer_profile: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quick_product_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    store: Mapped[Store] = relationship("Store")


class POSDraftSale(Base):
    __tablename__ = "pos_draft_sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    store: Mapped[Store] = relationship("Store")


class UserTOTPSecret(Base):
    __tablename__ = "user_totp_secrets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    secret: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="totp_secret")


class ActiveSession(Base):
    __tablename__ = "active_sessions"
    __table_args__ = (UniqueConstraint("session_token", name="uq_active_session_token"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_token: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    revoke_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped[User] = relationship(
        "User", foreign_keys=[user_id], back_populates="active_sessions"
    )
    revoked_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[revoked_by_id]
    )


class SyncOutbox(Base):
    __tablename__ = "sync_outbox"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", name="uq_outbox_entity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(80), nullable=False)
    operation: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


__all__ = [
    "CashRegisterSession",
    "CashSessionStatus",
    "Customer",
    "AuditLog",
    "BackupJob",
    "BackupMode",
    "ActiveSession",
    "DeviceIdentifier",
    "Device",
    "InventoryMovement",
    "MovementType",
    "PaymentMethod",
    "PurchaseOrder",
    "PurchaseOrderItem",
    "PurchaseReturn",
    "PurchaseStatus",
    "RepairOrder",
    "RepairOrderPart",
    "RepairStatus",
    "Role",
    "Store",
    "SupplierBatch",
    "SyncMode",
    "SyncSession",
    "SyncStatus",
    "Supplier",
    "SyncOutbox",
    "SyncOutboxPriority",
    "TransferOrder",
    "TransferOrderItem",
    "TransferStatus",
    "UserTOTPSecret",
    "StoreMembership",
    "User",
    "UserRole",
    "Sale",
    "SaleItem",
    "SaleReturn",
    "POSConfig",
    "POSDraftSale",
]
