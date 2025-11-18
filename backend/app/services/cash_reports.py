from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
from typing import Iterable, Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .. import models
from .locale_helpers import format_dual_currency

ACCENT_COLOR = colors.HexColor("#38bdf8")
BASE_DARK = colors.HexColor("#0f172a")
BASE_DIM = colors.HexColor("#111827")
TEXT_LIGHT = colors.HexColor("#e2e8f0")
BORDER_COLOR = colors.HexColor("#1e293b")


def _format_currency(value: Decimal | float | int) -> str:
    return format_dual_currency(value)


def _build_table(data: list[list[str]]) -> Table:
    table = Table(data, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BASE_DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), BASE_DIM),
                ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_LIGHT),
                ("LINEBEFORE", (0, 0), (0, -1), 1, BORDER_COLOR),
                ("LINEAFTER", (-1, 0), (-1, -1), 1, BORDER_COLOR),
                ("LINEABOVE", (0, 0), (-1, 0), 1.2, ACCENT_COLOR),
                ("LINEBELOW", (0, -1), (-1, -1), 1.2, ACCENT_COLOR),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def _signature_for_session(session: models.CashRegisterSession) -> str:
    payload = "|".join(
        [
            str(session.id),
            str(session.store_id),
            session.closed_at.isoformat() if session.closed_at else "",
            f"{Decimal(session.closing_amount or 0):.2f}",
            f"{Decimal(session.difference_amount or 0):.2f}",
            (session.difference_reason or ""),
        ]
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def render_cash_close_pdf(
    session: models.CashRegisterSession,
    entries: Sequence[models.CashRegisterEntry] | Iterable[models.CashRegisterEntry],
) -> bytes:
    """Genera un reporte PDF con el desglose del cierre de caja."""

    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, title="Reporte de cierre de caja POS")
    styles = getSampleStyleSheet()
    heading = ParagraphStyle(
        "HeadingSoftmobileCash",
        parent=styles["Heading1"],
        textColor=ACCENT_COLOR,
        fontSize=18,
    )

    store_label = session.store.name if getattr(session, "store", None) else f"Sucursal #{session.store_id}"
    now_label = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")
    elements: list = [  # type: ignore[var-annotated]
        Paragraph("Softmobile 2025 — Cierre de caja", heading),
        Spacer(1, 12),
        Paragraph(f"Generado automáticamente el {now_label}", styles["Normal"]),
        Spacer(1, 18),
    ]

    summary_rows = [
        ["Sesión", f"#{session.id}"],
        ["Sucursal", store_label],
        ["Estado", session.status.value.title()],
        ["Apertura", _format_currency(session.opening_amount or 0)],
        ["Esperado", _format_currency(session.expected_amount or 0)],
        ["Cierre contado", _format_currency(session.closing_amount or 0)],
        ["Diferencia", _format_currency(session.difference_amount or 0)],
    ]
    if session.difference_reason:
        summary_rows.append(["Motivo diferencia", session.difference_reason])
    if session.reconciliation_notes:
        summary_rows.append(["Conciliación", session.reconciliation_notes])

    elements.append(_build_table([["Indicador", "Valor"], *summary_rows]))
    elements.append(Spacer(1, 18))

    denominations = session.denomination_breakdown or {}
    if denominations:
        denomination_table: list[list[str]] = [["Denominación", "Cantidad", "Importe"]]
        total_cash = Decimal("0")
        for key, quantity in sorted(denominations.items(), key=lambda item: Decimal(item[0]), reverse=True):
            value = Decimal(key)
            count = int(quantity)
            line_total = value * count
            total_cash += line_total
            denomination_table.append([
                _format_currency(value),
                str(count),
                _format_currency(line_total),
            ])
        denomination_table.append(["Total efectivo", "", _format_currency(total_cash)])
        elements.append(Paragraph("Desglose de denominaciones", styles["Heading3"]))
        elements.append(Spacer(1, 6))
        elements.append(_build_table(denomination_table))
        elements.append(Spacer(1, 18))

    movement_table: list[list[str]] = [["Tipo", "Monto", "Motivo", "Registrado"]]
    sorted_entries = sorted(entries, key=lambda item: item.created_at)
    for entry in sorted_entries:
        movement_table.append(
            [
                entry.entry_type.value.title(),
                _format_currency(entry.amount),
                entry.reason,
                entry.created_at.strftime("%d/%m/%Y %H:%M"),
            ]
        )
    if len(movement_table) > 1:
        elements.append(Paragraph("Movimientos manuales", styles["Heading3"]))
        elements.append(Spacer(1, 6))
        elements.append(_build_table(movement_table))
        elements.append(Spacer(1, 18))

    signature = _signature_for_session(session)
    elements.append(Paragraph("Firma digital", styles["Heading3"]))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(signature, styles["Code"]))

    document.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


__all__ = ["render_cash_close_pdf"]
