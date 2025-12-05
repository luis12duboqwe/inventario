from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import crud, models
from ..config import settings
from backend.core.logging import logger as core_logger
from . import notifications
from .locale_helpers import format_dual_currency

logger = core_logger.bind(component=__name__)


@dataclass(slots=True)
class ReminderResult:
    """Resultado del envío de recordatorios automáticos."""

    customer_id: int
    channels: list[str]
    scheduled_for: datetime | None
    outstanding_amount: float


def _format_currency(value: float) -> str:
    return format_dual_currency(value)


def _send_whatsapp_message(*, to_number: str, message: str, reference: str | None = None) -> None:
    """Envía un mensaje de WhatsApp asegurando un loop aislado."""

    async def _deliver() -> None:
        await notifications.send_whatsapp_message(
            to_number=to_number, message=message, reference=reference
        )

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_deliver())
    finally:
        loop.close()


def _collect_target_customers(session: Session) -> Iterable[models.Customer]:
    stmt = select(models.Customer).where(
        models.Customer.outstanding_debt > 0,
        models.Customer.status != "inactivo",
    )
    return session.scalars(stmt)


def send_upcoming_due_reminders(session: Session) -> list[ReminderResult]:
    """Genera recordatorios de cuentas por cobrar para clientes con vencimientos próximos."""

    if not settings.accounts_receivable_reminders_enabled:
        return []

    days_before_due = max(0, settings.accounts_receivable_reminder_days_before_due)
    results: list[ReminderResult] = []
    now = datetime.now(timezone.utc)

    for customer in _collect_target_customers(session):
        summary = crud.get_customer_accounts_receivable(session, customer.id)
        total = summary.summary.total_outstanding
        if total <= 0:
            continue

        next_due = summary.summary.next_due_date
        has_overdue = any(entry.status == "overdue" for entry in summary.open_entries)
        should_send = has_overdue
        if not should_send and next_due is not None:
            delta_days = (next_due - now).days
            if delta_days <= days_before_due:
                should_send = True

        if not should_send:
            continue

        channels: list[str] = []
        due_label = next_due.strftime("%d/%m/%Y") if next_due else "lo antes posible"
        email_subject = f"Recordatorio de pago — {customer.name}"
        email_body = (
            f"Hola {customer.contact_name or customer.name},\n\n"
            f"Detectamos un saldo pendiente de {_format_currency(total)} en tu cuenta."
            f" Te pedimos completar el pago {('antes del ' + due_label) if next_due else 'a la brevedad'}.\n\n"
            f"Resumen rápido:\n"
            f"- Saldo pendiente: {_format_currency(total)}\n"
            f"- Días promedio en cartera: {summary.summary.average_days_outstanding:.1f}\n"
            f"- Crédito disponible: {_format_currency(summary.summary.available_credit)}\n\n"
            "Este recordatorio fue generado automáticamente por Softmobile 2025."\
            " En caso de dudas contacta a tu ejecutivo de cuenta."
        )
        whatsapp_message = (
            "Softmobile: saldo pendiente "
            f"{_format_currency(total)}. "
            f"{'Vence el ' + due_label if next_due else 'Regulariza a la brevedad.'}"
        )

        if customer.email:
            try:
                notifications.send_email_notification(
                    recipients=[customer.email],
                    subject=email_subject,
                    body=email_body,
                )
                channels.append("email")
            except notifications.NotificationError as exc:
                logger.warning(
                    "Error enviando recordatorio de cuentas por cobrar por correo",
                    customer_id=customer.id,
                    error=str(exc),
                )

        if customer.phone:
            try:
                _send_whatsapp_message(
                    to_number=customer.phone,
                    message=whatsapp_message,
                    reference=f"CXC-{customer.id}",
                )
                channels.append("whatsapp")
            except notifications.NotificationError as exc:
                logger.warning(
                    "Error enviando recordatorio de cuentas por cobrar por WhatsApp",
                    customer_id=customer.id,
                    error=str(exc),
                )
            except Exception as exc:  # pragma: no cover - fallback defensivo
                logger.warning(
                    "Error inesperado enviando WhatsApp de cuentas por cobrar",
                    customer_id=customer.id,
                    error=str(exc),
                )

        if not channels:
            continue

        logger.info(
            "Recordatorio de cuentas por cobrar enviado",
            customer_id=customer.id,
            channels=channels,
            next_due_date=next_due.isoformat() if next_due else None,
            outstanding_amount=total,
        )
        results.append(
            ReminderResult(
                customer_id=customer.id,
                channels=channels,
                scheduled_for=next_due,
                outstanding_amount=total,
            )
        )

    return results


__all__ = ["ReminderResult", "send_upcoming_due_reminders"]
