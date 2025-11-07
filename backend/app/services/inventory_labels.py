"""Generación de etiquetas PDF para dispositivos del inventario.

Usa ReportLab con tema oscuro corporativo y un código QR con referencia interna.
"""
from __future__ import annotations

from io import BytesIO
from decimal import Decimal

from reportlab.lib.pagesizes import A7
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr, code128
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from sqlalchemy.orm import Session

from .. import models


def _format_money(value: Decimal | float | int | None) -> str:
    if value is None:
        return "$0.00"
    try:
        number = float(value)
    except Exception:  # pragma: no cover - defensivo
        number = 0.0
    return f"${number:,.2f}"


def render_device_label_pdf(db: Session, store_id: int, device_id: int) -> tuple[bytes, str]:
    """Construye una etiqueta compacta en PDF para un dispositivo.

    - Tamaño: A7 apaisado (etiqueta pequeña).
    - Contenido: SKU, nombre, precio, IMEI/serie si existen, QR interno.
    - Valida pertenencia del dispositivo a la sucursal indicada.
    """

    device = db.get(models.Device, device_id)
    if device is None or int(device.store_id or 0) != int(store_id):
        raise LookupError("device_not_found")

    width, height = A7  # en puntos
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(width, height))

    # Fondo oscuro corporativo
    c.setFillColor(colors.HexColor("#0f172a"))
    c.rect(0, 0, width, height, fill=True, stroke=False)

    # Encabezado
    c.setFillColor(colors.HexColor("#38bdf8"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(6 * mm, height - 8 * mm, "Softmobile · Inventario")

    # Datos principales
    c.setFillColor(colors.HexColor("#e2e8f0"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(6 * mm, height - 14 * mm, (device.name or device.sku)[:36])

    c.setFont("Helvetica", 9)
    c.drawString(6 * mm, height - 19 * mm, f"SKU: {device.sku}")

    price_text = _format_money(device.unit_price or device.precio_venta or 0)
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#38bdf8"))
    c.drawString(6 * mm, height - 25 * mm, f"Precio: {price_text}")

    # IMEI/Serie si existen en el device o en su tabla de identificadores
    c.setFillColor(colors.HexColor("#e2e8f0"))
    c.setFont("Helvetica", 8)
    line_y = height - 30 * mm
    if getattr(device, "imei", None):
        c.drawString(6 * mm, line_y, f"IMEI: {device.imei}")
        line_y -= 4 * mm
    if getattr(device, "serial", None):
        c.drawString(6 * mm, line_y, f"SERIE: {device.serial}")
        line_y -= 4 * mm

    # Marca/Modelo/Color/Capacidad (GB) si existen
    brand = getattr(device, "marca", None)
    model = getattr(device, "modelo", None)
    color = getattr(device, "color", None)
    capacidad_gb = getattr(device, "capacidad_gb", None)
    spec_parts: list[str] = []
    if brand:
        spec_parts.append(str(brand))
    if model:
        spec_parts.append(str(model))
    if color:
        spec_parts.append(str(color))
    if capacidad_gb:
        try:
            gb_int = int(capacidad_gb)
            if gb_int > 0:
                spec_parts.append(f"{gb_int}GB")
        except Exception:
            pass
    if spec_parts:
        spec_line = " · ".join(spec_parts)[:60]
        c.setFillColor(colors.HexColor("#cbd5e1"))
        c.setFont("Helvetica", 8)
        c.drawString(6 * mm, max(6 * mm, line_y), spec_line)
        line_y -= 4 * mm

    # Código QR interno con referencia al dispositivo y sucursal
    qr_data = f"softmobile://device/{device.id}?store={store_id}"
    qrcode = qr.QrCodeWidget(qr_data)
    bounds = qrcode.getBounds()
    qr_width = 22 * mm
    qr_height = 22 * mm
    d = Drawing(qr_width, qr_height)
    d.add(qrcode)
    renderPDF.draw(d, c, width - qr_width - 6 * mm, 6 * mm)

    # Código de barras Code128 del SKU
    try:
        sku_text = str(device.sku)
    except Exception:  # pragma: no cover - defensivo
        sku_text = ""
    if sku_text:
        # Altura moderada y ancho adaptativo
        barcode_height = 12 * mm
        # barWidth controla densidad; elegimos 0.28 para etiqueta A7
        barcode = code128.Code128(
            sku_text, barHeight=barcode_height, barWidth=0.28)
        # Posicionamos en la esquina inferior izquierda, dejando margen y evitando solapar el QR
        max_barcode_width = width - (qr_width + 14 * mm)
        # Si excede, reducimos escalando horizontalmente
        scale_x = 1.0
        try:
            if barcode.width > max_barcode_width:
                scale_x = max(0.5, float(max_barcode_width) /
                              float(barcode.width))
        except Exception:
            scale_x = 1.0
        # Guardar estado, aplicar escala y dibujar
        c.saveState()
        c.translate(6 * mm, 6 * mm)
        c.scale(scale_x, 1.0)
        barcode.drawOn(c, 0, 0)
        c.restoreState()

    # Pie con sucursal
    store_name = device.store.name if device.store else ""
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#94a3b8"))
    c.drawRightString(width - 6 * mm, height - 8 * mm, store_name[:28])

    c.showPage()
    c.save()

    buffer.seek(0)
    filename = f"etiqueta_{store_id}_{device.sku}.pdf"
    return buffer.getvalue(), filename
