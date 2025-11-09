"""Utilidades para generar recibos POS en PDF."""

from __future__ import annotations

import base64
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing

from .. import models


_RTN_PATTERN = re.compile(r"(?:RTN|RFC|NIF|DOC(?:UMENTO)?)[\s:]*([A-Za-z0-9\-]+)", re.IGNORECASE)


def _ensure_page_space(pdf: canvas.Canvas, current_y: float, lines: int = 1) -> float:
    """Garantiza espacio suficiente en la página antes de dibujar más líneas."""

    # // [PACK34-receipt]
    required = 12 * lines
    if current_y - required < 40:
        pdf.showPage()
        pdf.setFont("Helvetica", 10)
        return letter[1] - 40
    return current_y


def _format_currency(value: Decimal | float | int | None) -> str:
    decimal_value = Decimal("0") if value is None else Decimal(str(value))
    quantized = decimal_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{quantized:.2f}"


def _extract_candidate(value: object | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _extract_customer_tax_id(sale: models.Sale) -> str | None:
    customer = getattr(sale, "customer", None)
    candidates: list[str] = []
    if customer is not None:
        for attr in ("tax_id", "taxId", "rtn", "document_id", "doc_id"):
            candidate = _extract_candidate(getattr(customer, attr, None))
            if candidate:
                candidates.append(candidate)
        history = getattr(customer, "history", None)
        if isinstance(history, list):
            for entry in history:
                if isinstance(entry, dict):
                    for key in ("tax_id", "taxId", "rtn", "document_id", "doc_id"):
                        candidate = _extract_candidate(entry.get(key))
                        if candidate:
                            candidates.append(candidate)
        notes = getattr(customer, "notes", None)
        if isinstance(notes, str):
            match = _RTN_PATTERN.search(notes)
            if match:
                candidates.append(match.group(1))
    if sale.notes:
        match = _RTN_PATTERN.search(sale.notes)
        if match:
            candidates.append(match.group(1))
    for candidate in candidates:
        if candidate:
            return candidate
    return None


def _extract_store_tax_id(sale: models.Sale) -> str | None:
    store = getattr(sale, "store", None)
    if store is None:
        return None
    for attr in ("tax_id", "taxId", "rtn", "document_id", "doc_id"):
        candidate = _extract_candidate(getattr(store, attr, None))
        if candidate:
            return candidate
    # Fallback corporativo: reutilizar el código de sucursal si no hay RTN dedicado
    return _extract_candidate(getattr(store, "code", None))


def render_receipt_pdf(sale: models.Sale, config: models.POSConfig) -> bytes:
    """Genera el PDF del recibo POS y devuelve los bytes en memoria."""

    # // [PACK34-receipt]
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    store_name = sale.store.name if sale.store else "Sucursal"
    pdf.setTitle(f"Recibo_{config.invoice_prefix}_{sale.id}")
    y_position = height - 40

    customer_tax_id = _extract_customer_tax_id(sale)
    store_tax_id = _extract_store_tax_id(sale)
    document_number = f"{config.invoice_prefix}-{sale.id:06d}"
    document_label = "Factura" if customer_tax_id else "Ticket"

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y_position, store_name)
    y_position -= 18
    pdf.setFont("Helvetica", 10)
    if sale.store and sale.store.location:
        pdf.drawString(40, y_position, sale.store.location)
        y_position -= 14

    if store_tax_id:
        pdf.drawString(40, y_position, f"RTN Negocio: {store_tax_id}")
        y_position -= 14

    pdf.drawString(40, y_position, f"{document_label}: {document_number}")
    y_position -= 14
    pdf.drawString(40, y_position, f"Fecha: {sale.created_at.strftime('%Y-%m-%d %H:%M')}")
    y_position -= 14
    if sale.customer_name:
        pdf.drawString(40, y_position, f"Cliente: {sale.customer_name}")
        y_position -= 14
    if customer_tax_id:
        pdf.drawString(40, y_position, f"RTN Cliente: {customer_tax_id}")
        y_position -= 14
    payment_method = getattr(sale, "payment_method", None)
    payment_label = payment_method.value if payment_method else "SIN PAGO"
    pdf.drawString(40, y_position, f"Método: {payment_label}")
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
            f"${_format_currency(getattr(item, 'total_line', None))}",
        )
        y_position -= 14
        pdf.drawString(
            60,
            y_position,
            "Precio: $%s  Descuento: $%s"
            % (
                _format_currency(getattr(item, "unit_price", None)),
                _format_currency(getattr(item, "discount_amount", 0)),
            ),
        )
        y_position -= 14

    y_position = _ensure_page_space(pdf, y_position, 4)
    pdf.line(40, y_position, width - 40, y_position)
    y_position -= 14
    pdf.drawRightString(
        width - 40,
        y_position,
        f"Subtotal: ${_format_currency(getattr(sale, 'subtotal_amount', None))}",
    )
    y_position -= 14
    pdf.drawRightString(
        width - 40,
        y_position,
        f"Impuestos ({_format_currency(config.tax_rate)}%): ${_format_currency(getattr(sale, 'tax_amount', None))}",
    )
    y_position -= 14
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawRightString(
        width - 40,
        y_position,
        f"Total: ${_format_currency(getattr(sale, 'total_amount', None))}",
    )
    y_position -= 20

    qr_payload = {
        "sale_id": sale.id,
        "doc": document_number,
        "total": _format_currency(getattr(sale, "total_amount", None)),
        "issued_at": sale.created_at.isoformat(),
        "type": document_label.lower(),
    }
    if customer_tax_id:
        qr_payload["customer_tax_id"] = customer_tax_id
    if sale.store_id:
        qr_payload["store_id"] = sale.store_id
    qr_data = json.dumps(qr_payload, ensure_ascii=False)

    qr_widget = qr.QrCodeWidget(qr_data)
    target_size = 110
    drawing = Drawing(target_size, target_size)
    drawing.add(qr_widget)
    renderPDF.draw(drawing, pdf, width - target_size - 40, 60)

    pdf.setFont("Helvetica", 9)
    pdf.drawString(40, 60, "Escanea el código para validar el comprobante.")

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

