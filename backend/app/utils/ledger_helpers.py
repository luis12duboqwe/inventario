"""
Utilidades para gestión de ledgers (libros contables) de clientes y proveedores.

Extraídas desde crud_legacy.py para separación de responsabilidades.
"""

from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.utils.decimal_helpers import to_decimal
from backend.app.core.transactions import flush_session


def ensure_debt_respects_limit(credit_limit: Decimal, outstanding: Decimal) -> None:
    """Valida que el saldo pendiente no supere el límite de crédito configurado."""
    normalized_limit = to_decimal(credit_limit).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    normalized_outstanding = to_decimal(outstanding).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if normalized_outstanding <= Decimal("0"):
        return
    if normalized_limit <= Decimal("0"):
        raise ValueError("customer_outstanding_exceeds_limit")
    if normalized_outstanding > normalized_limit:
        raise ValueError("customer_outstanding_exceeds_limit")


def validate_customer_credit(customer: models.Customer, pending_charge: Decimal) -> None:
    """Valida que un cargo adicional no exceda el límite de crédito."""
    amount = to_decimal(pending_charge)
    if amount <= Decimal("0"):
        return
    limit = to_decimal(customer.credit_limit)
    if limit <= Decimal("0"):
        raise ValueError("customer_credit_limit_exceeded")
    projected = (to_decimal(customer.outstanding_debt) + amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if projected > limit:
        raise ValueError("customer_credit_limit_exceeded")


def customer_ledger_payload(entry: models.CustomerLedgerEntry) -> dict[str, object]:
    """Serializa una entrada de ledger de cliente."""
    return {
        "id": entry.id,
        "customer_id": entry.customer_id,
        "entry_type": entry.entry_type.value,
        "reference_type": entry.reference_type,
        "reference_id": entry.reference_id,
        "amount": float(entry.amount),
        "balance_after": float(entry.balance_after),
        "note": entry.note,
        "details": entry.details,
        "created_at": entry.created_at.isoformat(),
        "created_by_id": entry.created_by_id,
    }


def supplier_ledger_payload(entry: models.SupplierLedgerEntry) -> dict[str, object]:
    """Serializa una entrada de ledger de proveedor."""
    return {
        "id": entry.id,
        "supplier_id": entry.supplier_id,
        "entry_type": entry.entry_type.value,
        "reference_type": entry.reference_type,
        "reference_id": entry.reference_id,
        "amount": float(entry.amount),
        "balance_after": float(entry.balance_after),
        "note": entry.note,
        "details": entry.details,
        "created_at": entry.created_at.isoformat(),
        "created_by_id": entry.created_by_id,
    }


def create_customer_ledger_entry(
    db: Session,
    *,
    customer: models.Customer,
    entry_type: models.CustomerLedgerEntryType,
    amount: Decimal,
    note: str | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
    details: dict[str, object] | None = None,
    created_by_id: int | None = None,
) -> models.CustomerLedgerEntry:
    """Crea una entrada en el ledger de cliente."""
    entry = models.CustomerLedgerEntry(
        customer_id=customer.id,
        entry_type=entry_type,
        reference_type=reference_type,
        reference_id=reference_id,
        amount=to_decimal(amount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP),
        balance_after=to_decimal(customer.outstanding_debt).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
        note=note,
        details=details or {},
        created_by_id=created_by_id,
    )
    db.add(entry)
    flush_session(db)
    return entry


def create_supplier_ledger_entry(
    db: Session,
    *,
    supplier: models.Supplier,
    entry_type: models.SupplierLedgerEntryType,
    amount: Decimal,
    note: str | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
    details: dict[str, object] | None = None,
    created_by_id: int | None = None,
) -> models.SupplierLedgerEntry:
    """Crea una entrada en el ledger de proveedor."""
    entry = models.SupplierLedgerEntry(
        supplier_id=supplier.id,
        entry_type=entry_type,
        reference_type=reference_type,
        reference_id=reference_id,
        amount=to_decimal(amount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP),
        balance_after=to_decimal(supplier.outstanding_debt).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
        note=note,
        details=details or {},
        created_by_id=created_by_id,
    )
    db.add(entry)
    flush_session(db)
    return entry
