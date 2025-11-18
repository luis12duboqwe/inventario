"""Utilidades para calcular calendarios y resúmenes de crédito."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List

from ..config import settings


DecimalLike = Decimal | float | int


def _to_decimal(value: DecimalLike) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _quantize_currency(value: DecimalLike) -> Decimal:
    return _to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class DebtSnapshot:
    previous_balance: Decimal
    new_charges: Decimal
    payments_applied: Decimal

    @property
    def remaining_balance(self) -> Decimal:
        remaining = (
            self.previous_balance + self.new_charges - self.payments_applied
        )
        if remaining < Decimal("0"):
            return Decimal("0.00")
        return remaining.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def build_debt_snapshot(
    *,
    previous_balance: DecimalLike,
    new_charges: DecimalLike,
    payments_applied: DecimalLike,
) -> DebtSnapshot:
    return DebtSnapshot(
        previous_balance=_quantize_currency(previous_balance),
        new_charges=_quantize_currency(new_charges),
        payments_applied=_quantize_currency(payments_applied),
    )


def build_credit_schedule(
    *,
    base_date: datetime | None = None,
    remaining_balance: DecimalLike,
    installments: int | None = None,
    frequency_days: int | None = None,
) -> List[dict[str, object]]:
    remaining = _quantize_currency(remaining_balance)
    if remaining <= Decimal("0"):
        return []

    today = datetime.utcnow().date()
    base_reference = base_date or datetime.utcnow()
    normalized_base = base_reference.replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    raw_installments = installments or getattr(settings, "default_credit_installments", 4)
    total_installments = max(1, min(int(raw_installments), 24))

    raw_frequency = frequency_days or getattr(settings, "default_credit_frequency_days", 15)
    step_days = max(7, min(int(raw_frequency), 60))

    base_amount = (remaining / Decimal(total_installments)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    schedule: list[dict[str, object]] = []
    accumulated = Decimal("0")

    for index in range(total_installments):
        if index == total_installments - 1:
            amount = remaining - accumulated
        else:
            amount = base_amount
        amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        accumulated += amount

        due_date = normalized_base + timedelta(days=step_days * (index + 1))
        days_until_due = (due_date.date() - today).days
        if days_until_due < 0:
            status = "overdue"
            reminder = (
                "Contacto urgente: coordinar regularización con el cliente."
            )
        elif days_until_due <= 3:
            status = "due_soon"
            reminder = "Enviar recordatorio personalizado en las próximas 24 horas."
        else:
            status = "pending"
            reminder = (
                "Programar seguimiento preventivo antes de la fecha de pago."
            )

        schedule.append(
            {
                "sequence": index + 1,
                "due_date": due_date,
                "amount": amount,
                "status": status,
                "reminder": reminder,
            }
        )

    return schedule


__all__ = [
    "DebtSnapshot",
    "build_credit_schedule",
    "build_debt_snapshot",
]

