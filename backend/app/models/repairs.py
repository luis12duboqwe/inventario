from __future__ import annotations
from typing import TYPE_CHECKING, Any, Optional, List, Dict
from datetime import datetime
from decimal import Decimal
import enum

from sqlalchemy import (
    Integer,
    String,
    Boolean,
    DateTime,
    Numeric,
    Text,
    ForeignKey,
    Enum,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base
from backend.app.models.stores import Store
from backend.app.models.customers import Customer
from backend.app.models.products import Device

if TYPE_CHECKING:
    from backend.app.models.sales import WarrantyClaim


class RepairStatus(str, enum.Enum):
    """Estados de una orden de reparación."""

    PENDIENTE = "PENDIENTE"
    EN_PROCESO = "EN_PROCESO"
    LISTO = "LISTO"
    ENTREGADO = "ENTREGADO"
    CANCELADO = "CANCELADO"  # // [PACK37-backend]

    @classmethod  # // [PACK37-backend]
    def _missing_(cls, value: object) -> "RepairStatus | None":
        if not isinstance(value, str):
            return None
        normalized = value.strip().upper()
        aliases: dict[str, "RepairStatus"] = {
            "NEW": cls.PENDIENTE,
            "IN_PROGRESS": cls.EN_PROCESO,
            "READY": cls.LISTO,
            "DELIVERED": cls.ENTREGADO,
            "CANCELLED": cls.CANCELADO,
        }
        return aliases.get(normalized)


class RepairPartSource(str, enum.Enum):  # // [PACK37-backend]
    """Origen del repuesto utilizado en la orden."""

    STOCK = "STOCK"
    EXTERNAL = "EXTERNAL"


class RepairOrder(Base):
    __tablename__ = "repair_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("clientes.id_cliente", ondelete="SET NULL"), nullable=True, index=True
    )
    customer_name: Mapped[str | None] = mapped_column(
        String(120), nullable=True)
    customer_contact: Mapped[str | None] = mapped_column(
        String(120), nullable=True)  # // [PACK37-backend]
    technician_name: Mapped[str] = mapped_column(String(120), nullable=False)
    damage_type: Mapped[str] = mapped_column(String(120), nullable=False)
    diagnosis: Mapped[str | None] = mapped_column(
        Text, nullable=True)  # // [PACK37-backend]
    device_model: Mapped[str | None] = mapped_column(
        String(120), nullable=True)  # // [PACK37-backend]
    imei: Mapped[str | None] = mapped_column(
        String(40), nullable=True)  # // [PACK37-backend]
    device_description: Mapped[str | None] = mapped_column(
        String(255), nullable=True)
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
    inventory_adjusted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    store: Mapped[Store] = relationship("Store")
    customer: Mapped[Customer | None] = relationship(
        "Customer", back_populates="repair_orders")
    parts: Mapped[list["RepairOrderPart"]] = relationship(
        "RepairOrderPart", back_populates="repair_order", cascade="all, delete-orphan"
    )
    warranty_claims: Mapped[list["WarrantyClaim"]] = relationship(
        "WarrantyClaim", back_populates="repair_order"
    )


class RepairOrderPart(Base):
    __tablename__ = "repair_order_parts"
    __table_args__ = (
        UniqueConstraint(
            "repair_order_id",
            "device_id",
            "part_name",
            name="uq_repair_order_part",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    repair_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repair_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    part_name: Mapped[str | None] = mapped_column(
        String(120), nullable=True)  # // [PACK37-backend]
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    source: Mapped[RepairPartSource] = mapped_column(  # // [PACK37-backend]
        Enum(RepairPartSource, name="repair_part_source"),
        nullable=False,
        default=RepairPartSource.STOCK,
    )

    repair_order: Mapped[RepairOrder] = relationship(
        "RepairOrder", back_populates="parts")
    device: Mapped[Device | None] = relationship("Device")
