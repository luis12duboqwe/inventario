from __future__ import annotations
from typing import TYPE_CHECKING, Any, Optional, List, Dict
from datetime import datetime, date
from decimal import Decimal
import enum

from sqlalchemy import (
    Integer,
    String,
    Boolean,
    DateTime,
    Date,
    Numeric,
    Text,
    ForeignKey,
    Enum,
    JSON,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base
from backend.app.models.users import User
from backend.app.models.stores import Store, Warehouse
from backend.app.models.products import Device
from backend.app.models.sales import (
    ReturnReasonCategory,
    ReturnDisposition,
    RETURN_REASON_CATEGORY_ENUM,
    RETURN_DISPOSITION_ENUM,
)

if TYPE_CHECKING:
    from backend.app.models.sales import Sale, RMARequest


class PurchaseStatus(str, enum.Enum):
    """Estados posibles de una orden de compra."""

    PENDIENTE = "PENDIENTE"
    BORRADOR = "BORRADOR"
    APROBADA = "APROBADA"
    EN_TRANSITO = "EN_TRANSITO"
    PARCIAL = "PARCIAL"
    RECIBIDA_TOTAL = "RECIBIDA_TOTAL"
    COMPLETADA = "COMPLETADA"
    ENVIADA = "ENVIADA"
    CANCELADA = "CANCELADA"
    RECHAZADA = "RECHAZADA"


class SupplierLedgerEntryType(str, enum.Enum):
    """Tipos de movimientos registrados en la bitácora de proveedores."""

    INVOICE = "invoice"
    PAYMENT = "payment"
    CREDIT_NOTE = "credit_note"
    ADJUSTMENT = "adjustment"


class SupplierLedgerEntry(Base):
    __tablename__ = "supplier_ledger_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    supplier_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_type: Mapped[SupplierLedgerEntryType] = mapped_column(
        Enum(SupplierLedgerEntryType, name="supplier_ledger_entry_type"),
        nullable=False,
    )
    reference_type: Mapped[str | None] = mapped_column(
        String(60), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    balance_after: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    created_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    supplier: Mapped["Supplier"] = relationship(
        "Supplier", back_populates="ledger_entries"
    )
    created_by: Mapped[Optional["User"]] = relationship("User")


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(120), nullable=False, unique=True, index=True)
    rtn: Mapped[str | None] = mapped_column(
        String(30), nullable=True, unique=True)
    payment_terms: Mapped[str | None] = mapped_column(
        String(80), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(
        String(120), nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    contact_info: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    products_supplied: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list)
    history: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list)
    outstanding_debt: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
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
    ledger_entries: Mapped[list["SupplierLedgerEntry"]] = relationship(
        "SupplierLedgerEntry",
        back_populates="supplier",
        cascade="all, delete-orphan",
    )


class SupplierBatch(Base):
    __tablename__ = "supplier_batches"
    __table_args__ = (
        UniqueConstraint("supplier_id", "batch_code",
                         name="uq_supplier_batch_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    supplier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    store_id: Mapped[int | None] = mapped_column(
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="SET NULL"),
        nullable=True,
        index=True,
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

    supplier: Mapped["Supplier"] = relationship(
        "Supplier", back_populates="batches")
    store: Mapped[Store | None] = relationship(
        "Store", back_populates="supplier_batches")
    device: Mapped[Device | None] = relationship("Device")


class Proveedor(Base):
    """Catálogo simplificado de proveedores corporativos."""

    __tablename__ = "proveedores"

    id_proveedor: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(
        String(150), nullable=False, unique=True, index=True)
    telefono: Mapped[str | None] = mapped_column(String(40), nullable=True)
    correo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tipo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    estado: Mapped[str] = mapped_column(
        String(40), nullable=False, default="activo")
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    compras: Mapped[list["Compra"]] = relationship(
        "Compra", back_populates="proveedor", cascade="all, delete-orphan"
    )


class Compra(Base):
    """Encabezado de compras directas registradas en el módulo clásico."""

    __tablename__ = "compras"

    id_compra: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True)
    proveedor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("proveedores.id_proveedor", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    usuario_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="RESTRICT"),
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
    estado: Mapped[str] = mapped_column(
        String(40), nullable=False, default="PENDIENTE")

    proveedor: Mapped[Proveedor] = relationship(
        "Proveedor", back_populates="compras")
    usuario: Mapped["User"] = relationship("User")
    detalles: Mapped[list["DetalleCompra"]] = relationship(
        "DetalleCompra", back_populates="compra", cascade="all, delete-orphan"
    )


class DetalleCompra(Base):
    """Detalle de productos asociados a una compra simplificada."""

    __tablename__ = "detalle_compras"

    id_detalle: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True)
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
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    supplier: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[PurchaseStatus] = mapped_column(
        Enum(PurchaseStatus, name="purchase_status"),
        nullable=False,
        default=PurchaseStatus.PENDIENTE,
    )
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    approved_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    requires_approval: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )

    store: Mapped[Store] = relationship("Store")
    created_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[created_by_id]
    )
    approved_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[approved_by_id]
    )
    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        "PurchaseOrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    returns: Mapped[list["PurchaseReturn"]] = relationship(
        "PurchaseReturn", back_populates="order", cascade="all, delete-orphan"
    )
    documents: Mapped[list["PurchaseOrderDocument"]] = relationship(
        "PurchaseOrderDocument",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="desc(PurchaseOrderDocument.uploaded_at)",
    )
    status_events: Mapped[list["PurchaseOrderStatusEvent"]] = relationship(
        "PurchaseOrderStatusEvent",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="PurchaseOrderStatusEvent.created_at",
    )


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    __table_args__ = (
        UniqueConstraint("purchase_order_id", "device_id",
                         name="uq_purchase_item_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_received: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0"))

    order: Mapped[PurchaseOrder] = relationship(
        "PurchaseOrder", back_populates="items")
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
    reason_category: Mapped[ReturnReasonCategory] = mapped_column(
        RETURN_REASON_CATEGORY_ENUM.copy(),
        nullable=False,
        default=ReturnReasonCategory.OTRO,
    )
    disposition: Mapped[ReturnDisposition] = mapped_column(
        RETURN_DISPOSITION_ENUM.copy(),
        nullable=False,
        default=ReturnDisposition.DEFECTUOSO,
    )
    warehouse_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    supplier_ledger_entry_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("supplier_ledger_entries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    corporate_reason: Mapped[str | None] = mapped_column(
        String(255), nullable=True)
    credit_note_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    processed_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    approved_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)

    order: Mapped[PurchaseOrder] = relationship(
        "PurchaseOrder", back_populates="returns")
    device: Mapped[Device] = relationship("Device")
    ledger_entry: Mapped[SupplierLedgerEntry | None] = relationship(
        "SupplierLedgerEntry"
    )
    processed_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[processed_by_id]
    )
    approved_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[approved_by_id]
    )
    warehouse: Mapped[Warehouse | None] = relationship(
        "Warehouse", foreign_keys=[warehouse_id]
    )

    rma_requests: Mapped[list["RMARequest"]] = relationship(
        "RMARequest",
        back_populates="purchase_return",
        cascade="all, delete-orphan",
    )


class PurchaseOrderDocument(Base):
    __tablename__ = "purchase_order_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(80), nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(20), nullable=False)
    object_path: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    uploaded_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True
    )

    order: Mapped[PurchaseOrder] = relationship(
        "PurchaseOrder", back_populates="documents")
    uploaded_by: Mapped[User | None] = relationship("User")


class PurchaseOrderStatusEvent(Base):
    __tablename__ = "purchase_order_status_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[PurchaseStatus] = mapped_column(
        Enum(PurchaseStatus, name="purchase_status"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    created_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True
    )

    order: Mapped[PurchaseOrder] = relationship(
        "PurchaseOrder", back_populates="status_events"
    )
    created_by: Mapped[User | None] = relationship("User")
