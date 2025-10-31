"""Utilidades para generar recibos POS en PDF."""

from __future__ import annotations

import base64
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from .. import models


def _ensure_page_space(pdf: canvas.Canvas, current_y: float, lines: int = 1) -> float:
    """Garantiza espacio suficiente en la página antes de dibujar más líneas."""

    # // [PACK34-receipt]
    required = 12 * lines
    if current_y - required < 40:
        pdf.showPage()
        pdf.setFont("Helvetica", 10)
        return letter[1] - 40
    return current_y


def render_receipt_pdf(sale: models.Sale, config: models.POSConfig) -> bytes:
    """Genera el PDF del recibo POS y devuelve los bytes en memoria."""

    # // [PACK34-receipt]
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    store_name = sale.store.name if sale.store else "Sucursal"
    pdf.setTitle(f"Recibo_{config.invoice_prefix}_{sale.id}")
    y_position = height - 40

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y_position, store_name)
    y_position -= 18
    pdf.setFont("Helvetica", 10)
    if sale.store and sale.store.location:
        pdf.drawString(40, y_position, sale.store.location)
        y_position -= 14

    pdf.drawString(40, y_position, f"Factura: {config.invoice_prefix}-{sale.id:06d}")
    y_position -= 14
    pdf.drawString(40, y_position, f"Fecha: {sale.created_at.strftime('%Y-%m-%d %H:%M')}")
    y_position -= 14
    if sale.customer_name:
        pdf.drawString(40, y_position, f"Cliente: {sale.customer_name}")
        y_position -= 14
    pdf.drawString(40, y_position, f"Método: {sale.payment_method.value}")
    y_position -= 20

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y_position, "Detalle")
    y_position -= 16
    pdf.setFont("Helvetica", 10)

    for item in sale.items:
        y_position = _ensure_page_space(pdf, y_position, 2)
        device_label = item.device.name if item.device else f"ID {item.device_id}"
        pdf.drawString(40, y_position, f"{device_label} · Cant: {item.quantity}")
        pdf.drawRightString(
            width - 40,
            y_position,
            f"${item.total_line:.2f}",
        )
        y_position -= 14
        pdf.drawString(
            60,
            y_position,
            f"Precio: ${item.unit_price:.2f}  Descuento: ${item.discount_amount:.2f}",
        )
        y_position -= 14

    y_position = _ensure_page_space(pdf, y_position, 4)
    pdf.line(40, y_position, width - 40, y_position)
    y_position -= 14
    pdf.drawRightString(width - 40, y_position, f"Subtotal: ${sale.subtotal_amount:.2f}")
    y_position -= 14
    pdf.drawRightString(
        width - 40,
        y_position,
        f"Impuestos ({float(config.tax_rate):.2f}%): ${sale.tax_amount:.2f}",
    )
    y_position -= 14
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawRightString(width - 40, y_position, f"Total: ${sale.total_amount:.2f}")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


def render_receipt_base64(sale: models.Sale, config: models.POSConfig) -> str:
    """Devuelve el recibo en formato base64 listo para la API."""

    # // [PACK34-receipt]
    pdf_bytes = render_receipt_pdf(sale, config)
    return base64.b64encode(pdf_bytes).decode("utf-8")


__all__ = [
    "render_receipt_pdf",
    "render_receipt_base64",
]

