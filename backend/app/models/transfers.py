from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from datetime import datetime
from decimal import Decimal
import enum

from sqlalchemy import (
    Integer,
    String,
    DateTime,
    Numeric,
    ForeignKey,
    Enum,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base
from backend.app.models.users import User
from backend.app.models.stores import Store
from backend.app.models.products import Device

if TYPE_CHECKING:
    from backend.app.models.inventory import InventoryReservation


class TransferStatus(str, enum.Enum):
    """Estados posibles de una orden de transferencia."""

    SOLICITADA = "SOLICITADA"
    EN_TRANSITO = "EN_TRANSITO"
    RECIBIDA = "RECIBIDA"
    RECHAZADA = "RECHAZADA"
    CANCELADA = "CANCELADA"


class TransferOrder(Base):
    __tablename__ = "transfer_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    origin_store_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    destination_store_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[TransferStatus] = mapped_column(
        Enum(TransferStatus, name="transfer_status"),
        nullable=False,
        default=TransferStatus.SOLICITADA,
    )
    requested_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    dispatched_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    received_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    cancelled_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    origin_store: Mapped[Store] = relationship(
        "Store", foreign_keys=[origin_store_id], backref="transfer_orders_out"
    )
    destination_store: Mapped[Store] = relationship(
        "Store", foreign_keys=[destination_store_id], backref="transfer_orders_in"
    )
    requested_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[requested_by_id])
    dispatched_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[dispatched_by_id])
    received_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[received_by_id])
    cancelled_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[cancelled_by_id])
    items: Mapped[list["TransferOrderItem"]] = relationship(
        "TransferOrderItem", back_populates="transfer_order", cascade="all, delete-orphan"
    )

    @property
    def origin_store_name(self) -> str:
        return self.origin_store.name

    @property
    def destination_store_name(self) -> str:
        return self.destination_store.name


class TransferOrderItem(Base):
    __tablename__ = "transfer_order_items"
    __table_args__ = (
        UniqueConstraint("transfer_order_id", "device_id",
                         name="uq_transfer_item_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    transfer_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("transfer_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    dispatched_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    received_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    dispatched_unit_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    reservation_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("inventory_reservations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    transfer_order: Mapped[TransferOrder] = relationship(
        "TransferOrder", back_populates="items"
    )
    device: Mapped[Device] = relationship("Device")
    reservation: Mapped[Optional["InventoryReservation"]] = relationship(
        "InventoryReservation"
    )
