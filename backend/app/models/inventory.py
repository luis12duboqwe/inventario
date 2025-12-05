from __future__ import annotations
import enum
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Any, List, Dict

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base
from backend.app.models.users import User
from backend.app.models.stores import Store, Warehouse
from backend.app.models.products import Device

if TYPE_CHECKING:
    from backend.app.models.sales import SaleItem
    from backend.app.models.transfers import TransferOrderItem


class MovementType(str, enum.Enum):
    """Tipos permitidos de movimientos de inventario."""

    IN = "entrada"
    OUT = "salida"
    ADJUST = "ajuste"


class InventoryState(str, enum.Enum):
    """Estados de ciclo de vida de una reserva de inventario."""

    RESERVADO = "RESERVADO"
    CONSUMIDO = "CONSUMIDO"
    CANCELADO = "CANCELADO"
    EXPIRADO = "EXPIRADO"


class StockMoveType(str, enum.Enum):
    """Clasificación de movimientos contables por sucursal."""

    IN = "IN"
    OUT = "OUT"
    ADJUST = "ADJ"
    TRANSFER = "TRANSFER"


class CostingMethod(str, enum.Enum):
    """Métodos de costeo soportados en la bitácora contable."""

    FIFO = "FIFO"
    AVG = "AVG"


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        Index(
            "ix_inventory_movements_store_fecha",
            "sucursal_destino_id",
            "fecha",
        ),
        Index("ix_inventory_movements_fecha", "fecha"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        "sucursal_destino_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="CASCADE"),
        index=True,
    )
    source_store_id: Mapped[int | None] = mapped_column(
        "sucursal_origen_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    warehouse_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_warehouse_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("warehouses.id", ondelete="SET NULL"),
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
    comment: Mapped[str | None] = mapped_column(
        "comentario", String(255), nullable=True)
    unit_cost: Mapped[Decimal | None] = mapped_column(
        "costo_unitario", Numeric(12, 2), nullable=True
    )
    performed_by_id: Mapped[int | None] = mapped_column(
        "usuario_id",
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        "fecha",
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
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
    warehouse: Mapped[Warehouse | None] = relationship(
        "Warehouse", foreign_keys=[warehouse_id], back_populates="inventory_movements"
    )
    source_warehouse: Mapped[Warehouse | None] = relationship(
        "Warehouse", foreign_keys=[source_warehouse_id], back_populates="source_inventory_movements"
    )
    device: Mapped[Device] = relationship("Device", back_populates="movements")
    performed_by: Mapped[User | None] = relationship(
        "User", back_populates="movements")

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

    @property
    def sucursal_origen(self) -> str | None:
        return self.tienda_origen

    @property
    def sucursal_destino(self) -> str | None:
        return self.tienda_destino


class InventoryReservation(Base):
    """Bloqueo temporal de existencias para ventas o transferencias."""

    __tablename__ = "inventory_reservations"
    __table_args__ = (
        Index("ix_inventory_reservation_store_device", "store_id", "device_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="CASCADE"),
        nullable=False,
    )
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    reserved_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
    )
    initial_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[InventoryState] = mapped_column(
        Enum(InventoryState, name="inventory_reservation_state"),
        nullable=False,
        default=InventoryState.RESERVADO,
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    resolution_reason: Mapped[str | None] = mapped_column(
        String(255), nullable=True)
    reference_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    store: Mapped[Store] = relationship("Store", back_populates="reservations")
    device: Mapped[Device] = relationship(
        "Device", back_populates="reservations")
    reserved_by: Mapped[User | None] = relationship(
        "User", back_populates="inventory_reservations", foreign_keys=[reserved_by_id]
    )
    resolved_by: Mapped[User | None] = relationship(
        "User", back_populates="resolved_reservations", foreign_keys=[resolved_by_id]
    )
    sale_items: Mapped[list["SaleItem"]] = relationship(
        "SaleItem", back_populates="reservation"
    )
    transfer_items: Mapped[list["TransferOrderItem"]] = relationship(
        "TransferOrderItem", back_populates="reservation"
    )


class StockMove(Base):
    __tablename__ = "stock_moves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    branch_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    movement_type: Mapped[StockMoveType] = mapped_column(
        Enum(StockMoveType, name="stock_move_type"), nullable=False
    )
    reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True
    )

    product: Mapped[Device] = relationship("Device")
    branch: Mapped[Store | None] = relationship("Store")
    ledger_entries: Mapped[list["CostLedgerEntry"]] = relationship(
        "CostLedgerEntry", back_populates="move", cascade="all, delete-orphan"
    )


class CostLedgerEntry(Base):
    __tablename__ = "cost_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    move_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stock_moves.id", ondelete="CASCADE"), nullable=False, index=True
    )
    branch_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    method: Mapped[CostingMethod] = mapped_column(
        Enum(CostingMethod, name="costing_method"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True
    )

    move: Mapped[StockMove] = relationship(
        "StockMove", back_populates="ledger_entries")
    product: Mapped[Device] = relationship("Device")
    branch: Mapped[Store | None] = relationship("Store")


class ImportValidation(Base):
    __tablename__ = "validaciones_importacion"

    id: Mapped[int] = mapped_column(
        "id_validacion", Integer, primary_key=True, index=True
    )
    producto_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    tipo: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    severidad: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
    corregido: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)

    device: Mapped[Device | None] = relationship(
        "Device", back_populates="validations"
    )


class InventoryImportTemp(Base):
    __tablename__ = "importaciones_temp"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre_archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    columnas_detectadas: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    registros_incompletos: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    total_registros: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    nuevos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actualizados: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    advertencias: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list)
    patrones_columnas: Mapped[dict[str, str]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    duracion_segundos: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
