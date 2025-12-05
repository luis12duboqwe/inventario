from __future__ import annotations
import enum
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Index,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .stores import Store, Warehouse
    from .users import User
    from .products import Device
    from .inventory import InventoryReservation
    from .purchases import PurchaseReturn
    from .repairs import RepairOrder
    from .customers import (
        Customer,
        LoyaltyAccount,
        StoreCredit,
        LoyaltyTransaction,
        StoreCreditRedemption,
    )


class PaymentMethod(str, enum.Enum):
    """Formas de pago soportadas en las ventas."""

    EFECTIVO = "EFECTIVO"
    TARJETA = "TARJETA"
    CREDITO = "CREDITO"
    TRANSFERENCIA = "TRANSFERENCIA"
    NOTA_CREDITO = "NOTA_CREDITO"
    PUNTOS = "PUNTOS"
    OTRO = "OTRO"


class POSDocumentType(str, enum.Enum):
    """Tipos de documento visibles en POS (catálogo básico)."""

    FACTURA = "FACTURA"
    TICKET = "TICKET"
    NOTA_CREDITO = "NOTA_CREDITO"
    NOTA_DEBITO = "NOTA_DEBITO"


class POSConfig(Base):
    __tablename__ = "pos_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sucursales.id_sucursal", ondelete="CASCADE"), nullable=False, unique=True
    )
    invoice_prefix: Mapped[str | None] = mapped_column(
        String(10), nullable=True)
    receipt_header: Mapped[str | None] = mapped_column(
        String(255), nullable=True)
    receipt_footer: Mapped[str | None] = mapped_column(
        String(255), nullable=True)
    printer_name: Mapped[str | None] = mapped_column(
        String(120), nullable=True)
    hardware_settings: Mapped[dict[str, Any] |
                              None] = mapped_column(JSON, nullable=True)
    promotions_config: Mapped[dict[str, Any] |
                              None] = mapped_column(JSON, nullable=True)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    auto_print: Mapped[bool] = mapped_column(Boolean, default=False)
    require_customer: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_discounts: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relaciones
    store: Mapped[Store] = relationship("Store")


class DTEStatus(str, enum.Enum):
    """Estados operativos de un documento tributario electrónico."""

    PENDIENTE = "PENDIENTE"
    EMITIDO = "EMITIDO"
    RECHAZADO = "RECHAZADO"
    ANULADO = "ANULADO"


class DTEDispatchStatus(str, enum.Enum):
    """Estados de la cola de envío de documentos tributarios."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class WarrantyStatus(str, enum.Enum):
    """Estados del ciclo de vida de una garantía asignada."""

    SIN_GARANTIA = "SIN_GARANTIA"
    ACTIVA = "ACTIVA"
    VENCIDA = "VENCIDA"
    RECLAMO = "RECLAMO"
    RESUELTA = "RESUELTA"
    ANULADA = "ANULADA"


class WarrantyClaimType(str, enum.Enum):
    """Tipos de reclamo soportados por las garantías."""

    REPARACION = "REPARACION"
    REEMPLAZO = "REEMPLAZO"


class WarrantyClaimStatus(str, enum.Enum):
    """Estados de procesamiento para los reclamos de garantía."""

    ABIERTO = "ABIERTO"
    EN_PROCESO = "EN_PROCESO"
    RESUELTO = "RESUELTO"
    CANCELADO = "CANCELADO"


class ReturnDisposition(str, enum.Enum):
    """Clasificación operativa de los artículos devueltos."""

    VENDIBLE = "vendible"
    DEFECTUOSO = "defectuoso"
    NO_VENDIBLE = "no_vendible"
    REPARACION = "reparacion"


class ReturnReasonCategory(str, enum.Enum):
    """Categorias corporativas para motivos de devolución."""

    DEFECTO = "defecto"
    LOGISTICA = "logistica"
    CLIENTE = "cliente"
    PRECIO = "precio"
    OTRO = "otro"


class RMAStatus(str, enum.Enum):
    """Flujos principales de una solicitud RMA."""

    PENDIENTE = "PENDIENTE"
    AUTORIZADA = "AUTORIZADA"
    EN_PROCESO = "EN_PROCESO"
    CERRADA = "CERRADA"


class CashSessionStatus(str, enum.Enum):
    """Ciclo de vida de un arqueo de caja POS."""

    ABIERTO = "ABIERTO"
    CERRADO = "CERRADO"


class CashEntryType(str, enum.Enum):
    """Tipos de movimientos manuales registrados en caja."""

    INGRESO = "INGRESO"
    EGRESO = "EGRESO"


class Sale(Base):
    __tablename__ = "ventas"

    id: Mapped[int] = mapped_column(
        "id_venta", Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[int | None] = mapped_column(
        "cliente_id",
        Integer,
        ForeignKey("clientes.id_cliente", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_name: Mapped[str | None] = mapped_column(
        String(120), nullable=True)
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
    loyalty_points_earned: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    loyalty_points_redeemed: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    status: Mapped[str] = mapped_column(
        "estado", String(30), nullable=False, default="COMPLETADA"
    )
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invoice_reported: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    invoice_reported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    invoice_annulled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    invoice_credit_note_code: Mapped[str | None] = mapped_column(
        String(32), nullable=True
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
    dte_status: Mapped[DTEStatus] = mapped_column(
        Enum(DTEStatus, name="dte_status"), nullable=False, default=DTEStatus.PENDIENTE
    )
    dte_reference: Mapped[str | None] = mapped_column(
        String(120), nullable=True, index=True
    )
    performed_by_id: Mapped[int | None] = mapped_column(
        "usuario_id",
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
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
    customer: Mapped[Customer | None] = relationship(
        "Customer", back_populates="sales")
    cash_session: Mapped[CashRegisterSession | None] = relationship(
        "CashRegisterSession", back_populates="sales"
    )
    items: Mapped[list["SaleItem"]] = relationship(
        "SaleItem", back_populates="sale", cascade="all, delete-orphan"
    )
    # Campos de documento para POS y facturación simple
    document_type: Mapped[POSDocumentType] = mapped_column(
        Enum(POSDocumentType, name="pos_document_type"), nullable=False, index=True, default=POSDocumentType.TICKET
    )
    document_number: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True)
    returns: Mapped[list["SaleReturn"]] = relationship(
        "SaleReturn", back_populates="sale", cascade="all, delete-orphan"
    )
    store_credit_redemptions: Mapped[list["StoreCreditRedemption"]] = relationship(
        "StoreCreditRedemption",
        back_populates="sale",
        cascade="all, delete-orphan",
    )
    loyalty_transactions: Mapped[list["LoyaltyTransaction"]] = relationship(
        "LoyaltyTransaction",
        back_populates="sale",
        cascade="all, delete-orphan",
    )
    dte_documents: Mapped[list["DTEDocument"]] = relationship(
        "DTEDocument", back_populates="sale", cascade="all, delete-orphan"
    )


class SaleItem(Base):
    __tablename__ = "detalle_ventas"

    id: Mapped[int] = mapped_column(
        "id_detalle", Integer, primary_key=True, index=True)
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
    reservation_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("inventory_reservations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    warranty_status: Mapped[WarrantyStatus | None] = mapped_column(
        Enum(WarrantyStatus, name="warranty_status"), nullable=True
    )

    sale: Mapped[Sale] = relationship("Sale", back_populates="items")
    device: Mapped[Device] = relationship("Device")
    reservation: Mapped[InventoryReservation | None] = relationship(
        "InventoryReservation", back_populates="sale_items"
    )
    warranty_assignment: Mapped["WarrantyAssignment | None"] = relationship(
        "WarrantyAssignment", back_populates="sale_item", uselist=False
    )


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
    reason_category: Mapped[ReturnReasonCategory] = mapped_column(
        Enum(ReturnReasonCategory, name="return_reason_category"),
        nullable=False,
        default=ReturnReasonCategory.OTRO,
    )
    disposition: Mapped[ReturnDisposition] = mapped_column(
        Enum(ReturnDisposition, name="return_disposition"),
        nullable=False,
        default=ReturnDisposition.VENDIBLE,
    )
    warehouse_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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

    sale: Mapped[Sale] = relationship("Sale", back_populates="returns")
    device: Mapped[Device] = relationship("Device")
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
        back_populates="sale_return",
        cascade="all, delete-orphan",
    )


class WarrantyAssignment(Base):
    __tablename__ = "warranty_assignments"
    __table_args__ = (
        UniqueConstraint("sale_item_id", name="uq_warranty_sale_item"),
        Index("ix_warranty_assignments_device_id", "device_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sale_item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("detalle_ventas.id_detalle", ondelete="CASCADE"),
        nullable=False,
    )
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    coverage_months: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    activation_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiration_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[WarrantyStatus] = mapped_column(
        Enum(WarrantyStatus, name="warranty_status"), nullable=False, default=WarrantyStatus.ACTIVA
    )
    serial_number: Mapped[str | None] = mapped_column(
        String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    sale_item: Mapped[SaleItem] = relationship(
        "SaleItem", back_populates="warranty_assignment"
    )
    device: Mapped[Device] = relationship(
        "Device", back_populates="warranty_assignments"
    )
    claims: Mapped[list["WarrantyClaim"]] = relationship(
        "WarrantyClaim",
        back_populates="assignment",
        cascade="all, delete-orphan",
    )


class WarrantyClaim(Base):
    __tablename__ = "warranty_claims"
    __table_args__ = (
        Index("ix_warranty_claim_assignment_id", "assignment_id"),
        Index("ix_warranty_claim_repair_order_id", "repair_order_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    assignment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("warranty_assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    claim_type: Mapped[WarrantyClaimType] = mapped_column(
        Enum(WarrantyClaimType, name="warranty_claim_type"), nullable=False
    )
    status: Mapped[WarrantyClaimStatus] = mapped_column(
        Enum(WarrantyClaimStatus, name="warranty_claim_status"), nullable=False, default=WarrantyClaimStatus.ABIERTO
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    performed_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
    )
    repair_order_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("repair_orders.id", ondelete="SET NULL"),
        nullable=True,
    )

    assignment: Mapped[WarrantyAssignment] = relationship(
        "WarrantyAssignment", back_populates="claims"
    )
    repair_order: Mapped["RepairOrder | None"] = relationship(
        "RepairOrder", back_populates="warranty_claims"
    )
    performed_by: Mapped[User | None] = relationship("User")


class PriceListItem(Base):
    """Precio específico de un dispositivo dentro de una lista."""

    __tablename__ = "price_list_items"
    __table_args__ = (
        UniqueConstraint(
            "price_list_id", "device_id", name="uq_price_list_items_price_device"
        ),
        Index("ix_price_list_items_list_device", "price_list_id", "device_id"),
        Index("ix_price_list_items_price_list", "price_list_id"),
        Index("ix_price_list_items_device", "device_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    price_list_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("price_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(10), nullable=False, default="MXN")
    discount_percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    price_list: Mapped[PriceList] = relationship(
        "PriceList", back_populates="items"
    )
    device: Mapped[Device] = relationship(
        "Device", back_populates="price_list_items"
    )


class PriceList(Base):
    """Catálogo de precios segmentado por sucursal o cliente."""

    __tablename__ = "price_lists"
    __table_args__ = (
        UniqueConstraint(
            "name", "store_id", "customer_id", name="uq_price_lists_scope_name"
        ),
        Index("ix_price_lists_name", "name"),
        Index("ix_price_lists_is_active", "is_active"),
        Index("ix_price_lists_priority", "priority"),
        Index("ix_price_lists_store_id", "store_id"),
        Index("ix_price_lists_customer_id", "customer_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)
    store_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="SET NULL"),
        nullable=True,
    )
    customer_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("clientes.id_cliente", ondelete="SET NULL"),
        nullable=True,
    )
    currency: Mapped[str] = mapped_column(
        String(10), nullable=False, default="MXN")
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    store: Mapped[Store | None] = relationship(
        "Store", back_populates="price_lists")
    customer: Mapped[Customer | None] = relationship(
        "Customer", back_populates="price_lists"
    )
    items: Mapped[list[PriceListItem]] = relationship(
        "PriceListItem", back_populates="price_list", cascade="all, delete-orphan"
    )

    @property
    def scope(self) -> str:
        if self.store_id is not None and self.customer_id is not None:
            return "store_customer"
        if self.customer_id is not None:
            return "customer"
        if self.store_id is not None:
            return "store"
        return "global"


class DTEDocument(Base):
    __tablename__ = "dte_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sale_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ventas.id_venta", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # authorization_id: Mapped[int] = mapped_column(
    #     Integer,
    #     ForeignKey("dte_authorizations.id", ondelete="SET NULL"),
    #     nullable=True,
    #     index=True,
    # )
    document_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True)
    serie: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    correlative: Mapped[int] = mapped_column(Integer, nullable=False)
    control_number: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True)
    cai: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    xml_content: Mapped[str] = mapped_column(Text, nullable=False)
    signature: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[DTEStatus] = mapped_column(
        Enum(DTEStatus, name="dte_status"), nullable=False, default=DTEStatus.PENDIENTE
    )
    reference_code: Mapped[str | None] = mapped_column(
        String(120), nullable=True)
    ack_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ack_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    sale: Mapped[Sale] = relationship("Sale", back_populates="dte_documents")


class CashRegisterSession(Base):
    __tablename__ = "cash_register_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="RESTRICT"),
        nullable=False,
        index=True,
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
    payment_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict)
    denomination_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict)
    reconciliation_notes: Mapped[str |
                                 None] = mapped_column(Text, nullable=True)
    difference_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    opened_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    closed_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    store: Mapped[Store] = relationship("Store")
    opened_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[opened_by_id], backref="cash_sessions_opened"
    )
    closed_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[closed_by_id], backref="cash_sessions_closed"
    )
    sales: Mapped[list[Sale]] = relationship(
        "Sale", back_populates="cash_session")
    # entries: Mapped[list["CashRegisterEntry"]] = relationship(
    #     "CashRegisterEntry",
    #     back_populates="session",
    # )


class RMARequest(Base):
    __tablename__ = "rma_requests"
    __table_args__ = (
        CheckConstraint(
            "(sale_return_id IS NOT NULL) <> (purchase_return_id IS NOT NULL)",
            name="ck_rma_single_return_reference",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sale_return_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sale_returns.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    purchase_return_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("purchase_returns.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    store_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[RMAStatus] = mapped_column(
        Enum(RMAStatus, name="rma_status"), nullable=False, default=RMAStatus.PENDIENTE
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    sale_return: Mapped[SaleReturn | None] = relationship(
        "SaleReturn", back_populates="rma_requests"
    )
    purchase_return: Mapped["PurchaseReturn | None"] = relationship(
        "PurchaseReturn", back_populates="rma_requests"
    )
    store: Mapped[Store] = relationship("Store")
    device: Mapped[Device] = relationship("Device")


class CashSession(Base):
    __tablename__ = "cash_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sucursales.id_sucursal"), nullable=False, index=True
    )
    status: Mapped[CashSessionStatus] = mapped_column(
        Enum(CashSessionStatus, name="cash_session_status"),
        default=CashSessionStatus.ABIERTO,
        nullable=False,
    )
    opening_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    closing_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    expected_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    difference_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    payment_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    denomination_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    reconciliation_notes: Mapped[str |
                                 None] = mapped_column(Text, nullable=True)
    difference_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    opened_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario"), nullable=True
    )
    closed_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario"), nullable=True
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relaciones
    store: Mapped[Store] = relationship("Store")
    opened_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[opened_by_id]
    )
    closed_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[closed_by_id]
    )
    entries: Mapped[list[CashEntry]] = relationship(
        "CashEntry", back_populates="session", cascade="all, delete-orphan"
    )


class CashEntry(Base):
    __tablename__ = "cash_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cash_sessions.id"), nullable=False, index=True
    )
    entry_type: Mapped[CashEntryType] = mapped_column(
        Enum(CashEntryType, name="cash_entry_type"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relaciones
    session: Mapped[CashSession] = relationship(
        "CashSession", back_populates="entries")
    created_by: Mapped[User | None] = relationship("User")


# Export Enums for compatibility
RETURN_DISPOSITION_ENUM = Enum(ReturnDisposition, name="return_disposition")
RETURN_REASON_CATEGORY_ENUM = Enum(
    ReturnReasonCategory, name="return_reason_category")
RMA_STATUS_ENUM = Enum(RMAStatus, name="rma_status")
WARRANTY_STATUS_ENUM = Enum(WarrantyStatus, name="warranty_status")
WARRANTY_CLAIM_STATUS_ENUM = Enum(
    WarrantyClaimStatus, name="warranty_claim_status")
WARRANTY_CLAIM_TYPE_ENUM = Enum(WarrantyClaimType, name="warranty_claim_type")
