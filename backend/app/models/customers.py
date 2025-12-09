from __future__ import annotations
from typing import TYPE_CHECKING, Any, Optional
from datetime import datetime, timezone
from decimal import Decimal
import enum
import secrets

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
from backend.app.models.users import User

if TYPE_CHECKING:
    from backend.app.models.sales import Sale, PriceList
    from backend.app.models.repairs import RepairOrder


def generate_customer_tax_id_placeholder() -> str:
    timestamp_component = datetime.now(timezone.utc).strftime("%y%m%d")
    random_component = f"{secrets.randbelow(10**8):08d}"
    digits = f"{timestamp_component}{random_component}"
    return f"{digits[:4]}-{digits[4:8]}-{digits[8:]}"


class CustomerType(str, enum.Enum):
    MINORISTA = "minorista"
    MAYORISTA = "mayorista"
    CORPORATIVO = "corporativo"
    VIP = "vip"


class CustomerStatus(str, enum.Enum):
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    BLOQUEADO = "bloqueado"
    MOROSO = "moroso"


class Customer(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(
        "id_cliente", Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        "nombre", String(120), nullable=False, unique=True, index=True
    )
    contact_name: Mapped[str | None] = mapped_column(
        String(120), nullable=True)
    email: Mapped[str | None] = mapped_column(
        "correo", String(120), nullable=True, unique=True, index=True
    )
    phone: Mapped[str] = mapped_column(
        "telefono", String(40), nullable=False, index=True
    )
    address: Mapped[str | None] = mapped_column(
        "direccion", String(255), nullable=True)
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
    history: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list)
    privacy_consents: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict)
    privacy_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict)
    segment_category: Mapped[str | None] = mapped_column(
        "segmento_categoria", String(60), nullable=True, index=True
    )
    tags: Mapped[list[str]] = mapped_column(
        "segmento_etiquetas", JSON, nullable=False, default=list
    )
    tax_id: Mapped[str] = mapped_column(
        "rtn",
        String(30),
        nullable=False,
        unique=True,
        index=True,
        default=generate_customer_tax_id_placeholder,
    )
    privacy_last_request_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
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
    sales: Mapped[list["Sale"]] = relationship(
        "Sale", back_populates="customer")
    ledger_entries: Mapped[list["CustomerLedgerEntry"]] = relationship(
        "CustomerLedgerEntry",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    store_credits: Mapped[list["StoreCredit"]] = relationship(
        "StoreCredit",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    privacy_requests: Mapped[list["CustomerPrivacyRequest"]] = relationship(
        "CustomerPrivacyRequest",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    price_lists: Mapped[list["PriceList"]] = relationship(
        "PriceList",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    loyalty_account: Mapped[Optional["LoyaltyAccount"]] = relationship(
        "LoyaltyAccount",
        back_populates="customer",
        cascade="all, delete-orphan",
        uselist=False,
    )
    segment_snapshot: Mapped[Optional["CustomerSegmentSnapshot"]] = relationship(
        "CustomerSegmentSnapshot",
        back_populates="customer",
        cascade="all, delete-orphan",
        uselist=False,
    )

    @property
    def annual_purchase_amount(self) -> Decimal:
        snapshot = getattr(self, "segment_snapshot", None)
        if snapshot and snapshot.annual_amount is not None:
            return Decimal(snapshot.annual_amount)
        return Decimal("0")

    @property
    def orders_last_year(self) -> int:
        snapshot = getattr(self, "segment_snapshot", None)
        return int(snapshot.orders_last_year) if snapshot else 0

    @property
    def purchase_frequency(self) -> str:
        snapshot = getattr(self, "segment_snapshot", None)
        return snapshot.frequency_label if snapshot else "sin_datos"

    @property
    def segment_labels(self) -> list[str]:
        snapshot = getattr(self, "segment_snapshot", None)
        if snapshot and snapshot.segment_labels:
            return list(snapshot.segment_labels)
        return []

    @property
    def last_purchase_at(self) -> datetime | None:
        snapshot = getattr(self, "segment_snapshot", None)
        return snapshot.last_sale_at if snapshot else None


class PrivacyRequestType(str, enum.Enum):
    """Tipos de solicitudes de privacidad realizadas por clientes."""

    CONSENT = "consent"
    ANONYMIZATION = "anonymization"


class PrivacyRequestStatus(str, enum.Enum):
    """Estados posibles de una solicitud de privacidad."""

    REGISTRADA = "registrada"
    PROCESADA = "procesada"


class CustomerPrivacyRequest(Base):
    __tablename__ = "customer_privacy_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clientes.id_cliente", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    request_type: Mapped[PrivacyRequestType] = mapped_column(
        Enum(PrivacyRequestType, name="privacy_request_type"), nullable=False
    )
    status: Mapped[PrivacyRequestStatus] = mapped_column(
        Enum(PrivacyRequestStatus, name="privacy_request_status"),
        nullable=False,
        default=PrivacyRequestStatus.PROCESADA,
    )
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consent_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    masked_fields: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    requested_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processed_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    customer: Mapped[Customer] = relationship(
        "Customer", back_populates="privacy_requests"
    )
    requested_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[requested_by_id]
    )
    processed_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[processed_by_id]
    )


class CustomerLedgerEntryType(str, enum.Enum):
    """Tipos de movimientos registrados en la bitácora de clientes."""

    SALE = "sale"
    PAYMENT = "payment"
    ADJUSTMENT = "adjustment"
    NOTE = "note"
    STORE_CREDIT_ISSUED = "store_credit_issued"
    STORE_CREDIT_REDEEMED = "store_credit_redeemed"


class CustomerLedgerEntry(Base):
    __tablename__ = "customer_ledger_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clientes.id_cliente", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_type: Mapped[CustomerLedgerEntryType] = mapped_column(
        Enum(CustomerLedgerEntryType, name="customer_ledger_entry_type"),
        nullable=False,
    )
    reference_type: Mapped[str | None] = mapped_column(
        String(40), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    created_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    customer: Mapped["Customer"] = relationship(
        "Customer", back_populates="ledger_entries"
    )
    created_by: Mapped[Optional["User"]] = relationship("User")


class LoyaltyTransactionType(str, enum.Enum):
    """Clasificación corporativa de movimientos de lealtad."""

    EARN = "earn"
    REDEEM = "redeem"
    ADJUST = "adjust"
    EXPIRATION = "expiration"


class LoyaltyAccount(Base):
    __tablename__ = "loyalty_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clientes.id_cliente", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    accrual_rate: Mapped[Decimal] = mapped_column(
        Numeric(6, 4), nullable=False, default=Decimal("1.0000")
    )
    redemption_rate: Mapped[Decimal] = mapped_column(
        Numeric(6, 4), nullable=False, default=Decimal("1.0000")
    )
    expiration_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=365)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)
    rule_config: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    balance_points: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    lifetime_points_earned: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    lifetime_points_redeemed: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    expired_points_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    last_accrual_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_redemption_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_expiration_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    customer: Mapped["Customer"] = relationship(
        "Customer", back_populates="loyalty_account"
    )
    transactions: Mapped[list["LoyaltyTransaction"]] = relationship(
        "LoyaltyTransaction",
        back_populates="account",
        cascade="all, delete-orphan",
    )


class LoyaltyTransaction(Base):
    __tablename__ = "loyalty_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("loyalty_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sale_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("ventas.id_venta", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    transaction_type: Mapped[LoyaltyTransactionType] = mapped_column(
        Enum(LoyaltyTransactionType, name="loyalty_transaction_type"), nullable=False
    )
    points: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    currency_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    registered_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    account: Mapped["LoyaltyAccount"] = relationship(
        "LoyaltyAccount", back_populates="transactions"
    )
    sale: Mapped["Sale | None"] = relationship(
        "Sale", back_populates="loyalty_transactions"
    )
    registered_by: Mapped[Optional["User"]] = relationship("User")


class StoreCreditStatus(str, enum.Enum):
    """Estados operativos de las notas de crédito emitidas."""

    ACTIVO = "ACTIVO"
    PARCIAL = "PARCIAL"
    REDIMIDO = "REDIMIDO"
    CANCELADO = "CANCELADO"


class StoreCredit(Base):
    __tablename__ = "store_credits"
    __table_args__ = (
        UniqueConstraint("code", name="uq_store_credit_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clientes.id_cliente", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    issued_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    balance_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    status: Mapped[StoreCreditStatus] = mapped_column(
        Enum(StoreCreditStatus, name="store_credit_status"),
        nullable=False,
        default=StoreCreditStatus.ACTIVO,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    redeemed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    issued_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    customer: Mapped["Customer"] = relationship(
        "Customer", back_populates="store_credits"
    )
    issued_by: Mapped[Optional["User"]] = relationship("User")
    redemptions: Mapped[list["StoreCreditRedemption"]] = relationship(
        "StoreCreditRedemption",
        back_populates="store_credit",
        cascade="all, delete-orphan",
    )


class CustomerSegmentSnapshot(Base):
    __tablename__ = "customer_segment_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clientes.id_cliente", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    annual_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    orders_last_year: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    average_ticket: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    frequency_label: Mapped[str] = mapped_column(
        String(30), nullable=False, default="sin_datos"
    )
    segment_labels: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    last_sale_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    customer: Mapped[Customer] = relationship(
        "Customer", back_populates="segment_snapshot"
    )


class StoreCreditRedemption(Base):
    __tablename__ = "store_credit_redemptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_credit_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("store_credits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sale_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("ventas.id_venta", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    store_credit: Mapped[StoreCredit] = relationship(
        "StoreCredit", back_populates="redemptions"
    )
    sale: Mapped["Sale | None"] = relationship("Sale")
    created_by: Mapped["User | None"] = relationship("User")


# Export Enums for compatibility
LOYALTY_TRANSACTION_TYPE_ENUM = LoyaltyTransactionType
