from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base

if TYPE_CHECKING:
    from backend.app.models.products import Device, ProductBundle
    from backend.app.models.inventory import InventoryMovement
    from backend.app.models.users import User
    from backend.app.models.customers import Customer
    from backend.app.models.sales import PriceList
    from backend.app.models.purchases import SupplierBatch
    from backend.app.models.sync import SyncSession


class Store(Base):
    __tablename__ = "sucursales"
    __table_args__ = (Index("ix_sucursales_is_deleted", "is_deleted"),)

    id: Mapped[int] = mapped_column(
        "id_sucursal", Integer, primary_key=True, index=True
    )
    name: Mapped[str] = mapped_column(
        "nombre", String(120), nullable=False, unique=True, index=True
    )
    location: Mapped[str | None] = mapped_column(
        "direccion", String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(
        "telefono", String(30), nullable=True)
    manager: Mapped[str | None] = mapped_column(
        "responsable", String(120), nullable=True)
    status: Mapped[str] = mapped_column(
        "estado", String(30), nullable=False, default="activa", index=True
    )
    code: Mapped[str] = mapped_column(
        "codigo", String(20), nullable=False, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        "fecha_creacion", DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    timezone: Mapped[str] = mapped_column(
        String(50), nullable=False, default="UTC")
    inventory_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    devices: Mapped[list["Device"]] = relationship(
        "Device",
        back_populates="store",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    movements: Mapped[list["InventoryMovement"]] = relationship(
        "InventoryMovement",
        back_populates="store",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="InventoryMovement.store_id",
    )
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="store",
        passive_deletes=True,
        primaryjoin="and_(foreign(User.store_id)==Store.id, Store.is_deleted.is_(False))",
    )
    warehouses: Mapped[list["Warehouse"]] = relationship(
        "Warehouse", back_populates="store", cascade="all, delete-orphan"
    )
    bundles: Mapped[list["ProductBundle"]] = relationship(
        "ProductBundle", back_populates="store", cascade="all, delete-orphan"
    )
    reservations: Mapped[list["InventoryReservation"]] = relationship(
        "InventoryReservation", back_populates="store", cascade="all, delete-orphan"
    )
    price_lists: Mapped[list["PriceList"]] = relationship(
        "PriceList", back_populates="store", cascade="all, delete-orphan"
    )
    supplier_batches: Mapped[list["SupplierBatch"]] = relationship(
        "SupplierBatch", back_populates="store", cascade="all, delete-orphan"
    )
    sync_sessions: Mapped[list["SyncSession"]] = relationship(
        "SyncSession", back_populates="store", cascade="all, delete-orphan"
    )


class Warehouse(Base):
    __tablename__ = "warehouses"

    __table_args__ = (
        UniqueConstraint("store_id", "code", name="uq_warehouse_store_code"),
        UniqueConstraint("store_id", "name", name="uq_warehouse_store_name"),
        Index("ix_warehouses_store_id", "store_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sucursales.id_sucursal", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    store: Mapped[Store] = relationship("Store", back_populates="warehouses")
    devices: Mapped[list["Device"]] = relationship(
        "Device", back_populates="warehouse")
    inventory_movements: Mapped[list["InventoryMovement"]] = relationship(
        "InventoryMovement",
        back_populates="warehouse",
        foreign_keys="InventoryMovement.warehouse_id",
        cascade="all, delete-orphan",
    )
    source_inventory_movements: Mapped[list["InventoryMovement"]] = relationship(
        "InventoryMovement",
        back_populates="source_warehouse",
        foreign_keys="InventoryMovement.source_warehouse_id",
        cascade="all, delete-orphan",
    )


class WMSBin(Base):
    """Ubicación física (bin) dentro de una sucursal para WMS ligero."""

    __tablename__ = "wms_bins"
    __table_args__ = (
        UniqueConstraint("sucursal_id", "codigo",
                         name="uq_wms_bins_store_code"),
        Index("ix_wms_bins_store", "sucursal_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column("codigo", String(60), nullable=False)
    aisle: Mapped[str | None] = mapped_column(
        "pasillo", String(60), nullable=True)
    rack: Mapped[str | None] = mapped_column(String(60), nullable=True)
    level: Mapped[str | None] = mapped_column(
        "nivel", String(60), nullable=True)
    description: Mapped[str | None] = mapped_column(
        "descripcion", String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column("fecha_creacion", DateTime(
        timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column("fecha_actualizacion", DateTime(
        timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    store: Mapped[Store] = relationship("Store")
    assignments: Mapped[list["DeviceBinAssignment"]] = relationship(
        "DeviceBinAssignment", back_populates="bin", cascade="all, delete-orphan"
    )


class DeviceBinAssignment(Base):
    """Asociación actual/histórica entre un dispositivo y un bin."""

    __tablename__ = "device_bins"
    __table_args__ = (
        Index("ix_device_bins_device", "producto_id"),
        Index("ix_device_bins_bin", "bin_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(
        "producto_id", Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    bin_id: Mapped[int] = mapped_column(Integer, ForeignKey(
        "wms_bins.id", ondelete="CASCADE"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column("asignado_en", DateTime(
        timezone=True), default=datetime.utcnow, nullable=False)
    unassigned_at: Mapped[datetime | None] = mapped_column(
        "desasignado_en", DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(
        "activo", Boolean, default=True, nullable=False)

    device: Mapped[Device] = relationship("Device")
    bin: Mapped[WMSBin] = relationship("WMSBin", back_populates="assignments")
