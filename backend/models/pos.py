"""Modelos SQLAlchemy simplificados para el módulo POS ligero."""
from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship

BasePOS = declarative_base()


class SaleStatus(str, enum.Enum):
    """Ciclo de vida de una venta POS dentro del wrapper ligero."""

    OPEN = "OPEN"
    HELD = "HELD"
    COMPLETED = "COMPLETED"
    VOID = "VOID"


class PaymentMethod(str, enum.Enum):
    """Formas de pago habilitadas para el POS comercial."""

    CASH = "CASH"
    CARD = "CARD"
    TRANSFER = "TRANSFER"
    STORE_CREDIT = "STORE_CREDIT"


class Sale(BasePOS):
    """Encabezado de venta POS con totales consolidados."""

    __tablename__ = "pos_sales"
    __table_args__ = (
        CheckConstraint("subtotal_amount >= 0", name="ck_pos_sales_subtotal_positive"),
        CheckConstraint("discount_total >= 0", name="ck_pos_sales_discount_positive"),
        CheckConstraint("tax_total >= 0", name="ck_pos_sales_tax_positive"),
        CheckConstraint("total_amount >= 0", name="ck_pos_sales_total_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[SaleStatus] = mapped_column(
        Enum(SaleStatus, name="pos_sale_status"),
        default=SaleStatus.OPEN,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subtotal_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    discount_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    tax_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
    held_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))

    items: Mapped[list["SaleItem"]] = relationship(
        back_populates="sale", cascade="all, delete-orphan", lazy="joined"
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="sale", cascade="all, delete-orphan", lazy="joined"
    )

    def recompute_totals(self) -> None:
        """Actualiza los totales de la venta con base en los renglones actuales."""

        subtotal = sum((item.line_subtotal for item in self.items), Decimal("0"))
        discount = sum((item.discount_amount for item in self.items), Decimal("0"))
        tax = sum((item.tax_amount for item in self.items), Decimal("0"))
        total = sum((item.total_amount for item in self.items), Decimal("0"))
        self.subtotal_amount = subtotal.quantize(Decimal("0.01"))
        self.discount_total = discount.quantize(Decimal("0.01"))
        self.tax_total = tax.quantize(Decimal("0.01"))
        self.total_amount = total.quantize(Decimal("0.01"))
        self.updated_at = datetime.utcnow()


class SaleItem(BasePOS):
    """Detalle de producto/servicio asociado a una venta POS."""

    __tablename__ = "pos_sale_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_pos_sale_items_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_pos_sale_items_unit_price_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(
        ForeignKey("pos_sales.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0"), nullable=False
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    line_subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )

    sale: Mapped[Sale] = relationship(back_populates="items")


class Payment(BasePOS):
    """Registro de pago capturado en una venta POS."""

    __tablename__ = "pos_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(
        ForeignKey("pos_sales.id", ondelete="CASCADE"), nullable=False, index=True
    )
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="pos_payment_method"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    sale: Mapped[Sale] = relationship(back_populates="payments")


__all__ = [
    "Payment",
    "PaymentMethod",
    "Sale",
    "SaleItem",
    "SaleStatus",
]
