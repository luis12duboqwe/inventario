"""Generación de etiquetas en PDF, ZPL y ESC/POS.

Usa ReportLab con tema oscuro corporativo y comandos de impresora
para Zebra/Epson. Incluye QR interno y código de barras del SKU.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from io import BytesIO
from typing import NamedTuple

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr, code128
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from sqlalchemy.orm import Session

from .. import models, schemas


@dataclass(frozen=True, slots=True)
class LabelTemplateSpec:
    """Describe un tamaño de etiqueta soportado."""

    key: schemas.LabelTemplateKey
    width_mm: float
    height_mm: float
    description: str


class LabelContext(NamedTuple):
    """Datos base de la etiqueta a renderizar."""

    store_id: int
    store_name: str
    sku: str
    name: str
    price_text: str
    identifiers: list[str]
    qr_data: str
    spec_line: str | None


LABEL_TEMPLATES: dict[schemas.LabelTemplateKey, LabelTemplateSpec] = {
    schemas.LabelTemplateKey.SIZE_38X25: LabelTemplateSpec(
        key=schemas.LabelTemplateKey.SIZE_38X25,
        width_mm=38,
        height_mm=25,
        description="Etiqueta compacta 38×25 mm",
    ),
    schemas.LabelTemplateKey.SIZE_50X30: LabelTemplateSpec(
        key=schemas.LabelTemplateKey.SIZE_50X30,
        width_mm=50,
        height_mm=30,
        description="Etiqueta estándar 50×30 mm",
    ),
    schemas.LabelTemplateKey.SIZE_80X50: LabelTemplateSpec(
        key=schemas.LabelTemplateKey.SIZE_80X50,
        width_mm=80,
        height_mm=50,
        description="Etiqueta ampliada 80×50 mm",
    ),
    schemas.LabelTemplateKey.A7: LabelTemplateSpec(
        key=schemas.LabelTemplateKey.A7,
        width_mm=74,
        height_mm=105,
        description="Etiqueta A7 apaisada",
    ),
}


def _format_money(value: Decimal | float | int | None) -> str:
    if value is None:
        return "$0.00"
    try:
        number = float(value)
    except Exception:  # pragma: no cover - defensivo
        number = 0.0
    return f"${number:,.2f}"


def _collect_identifier_lines(device: models.Device) -> list[str]:
    """Reúne identificadores únicos del dispositivo para mostrarlos en la etiqueta."""

    identifiers: list[tuple[str, str | None]] = [
        ("IMEI", getattr(device, "imei", None)),
        ("SERIE", getattr(device, "serial", None)),
    ]

    extra = getattr(device, "identifier", None)
    if extra is not None:
        identifiers.extend(
            (
                ("IMEI", getattr(extra, "imei_1", None)),
                ("IMEI 2", getattr(extra, "imei_2", None)),
                ("SERIE", getattr(extra, "numero_serie", None)),
            )
        )

    unique_values: set[str] = set()
    lines: list[str] = []
    for label, raw in identifiers:
        if raw is None:
            continue
        text = str(raw).strip()
        if not text or text in unique_values:
            continue
        unique_values.add(text)
        lines.append(f"{label}: {text}")
    return lines


def _resolve_template(
    template_key: schemas.LabelTemplateKey | None,
) -> LabelTemplateSpec:
    """Obtiene la plantilla solicitada o devuelve una predeterminada."""

    if template_key and template_key in LABEL_TEMPLATES:
        return LABEL_TEMPLATES[template_key]
    return LABEL_TEMPLATES[schemas.LabelTemplateKey.SIZE_38X25]


def _build_label_context(
    db: Session, store_id: int, device_id: int
) -> tuple[LabelContext, models.Device]:
    device = db.get(models.Device, device_id)
    if device is None or int(device.store_id or 0) != int(store_id):
        raise LookupError("device_not_found")

    identifiers = _collect_identifier_lines(device)
    price_text = _format_money(device.unit_price or device.precio_venta or 0)
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
    spec_line = " · ".join(spec_parts)[:60] if spec_parts else None

    context = LabelContext(
        store_id=store_id,
        store_name=device.store.name if device.store else "",
        sku=str(device.sku),
        name=(device.name or device.sku)[:60],
        price_text=price_text,
        identifiers=identifiers,
        qr_data=f"softmobile://device/{device.id}?store={store_id}",
        spec_line=spec_line,
    )
    return context, device


def render_device_label_pdf(
    db: Session,
    store_id: int,
    device_id: int,
    *,
    template_key: schemas.LabelTemplateKey | None = None,
) -> tuple[bytes, str]:
    """Construye una etiqueta compacta en PDF para un dispositivo."""

    context, _device = _build_label_context(db, store_id, device_id)
    template = _resolve_template(template_key)
    width = template.width_mm * mm
    height = template.height_mm * mm
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(width, height))

    # Fondo oscuro corporativo
    c.setFillColor(colors.HexColor("#0f172a"))
    c.rect(0, 0, width, height, fill=True, stroke=False)

    # Encabezado
    c.setFillColor(colors.HexColor("#38bdf8"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(5 * mm, height - 7 * mm, "Softmobile · Inventario")

    # Datos principales
    c.setFillColor(colors.HexColor("#e2e8f0"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(5 * mm, height - 13 * mm, context.name[:40])

    c.setFont("Helvetica", 8)
    c.drawString(5 * mm, height - 18 * mm, f"SKU: {context.sku}")

    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor("#38bdf8"))
    c.drawString(5 * mm, height - 23 * mm, f"Precio: {context.price_text}")

    # IMEI/Serie si existen
    c.setFillColor(colors.HexColor("#e2e8f0"))
    c.setFont("Helvetica", 7)
    line_y = height - 27 * mm
    for identifier_line in context.identifiers:
        if line_y < 7 * mm:
            break
        c.drawString(5 * mm, line_y, identifier_line[:64])
        line_y -= 3.5 * mm

    # Marca/Modelo/Color/Capacidad (GB) si existen
    if context.spec_line:
        c.setFillColor(colors.HexColor("#cbd5e1"))
        c.setFont("Helvetica", 7)
        c.drawString(5 * mm, max(6 * mm, line_y), context.spec_line)
        line_y -= 3 * mm

    # Código QR interno con referencia al dispositivo y sucursal
    qrcode = qr.QrCodeWidget(context.qr_data)
    qr_width = min(20 * mm, height / 3)
    qr_height = qr_width
    drawing = Drawing(qr_width, qr_height)
    drawing.add(qrcode)
    renderPDF.draw(drawing, c, width - qr_width - 5 * mm, 5 * mm)

    # Código de barras Code128 del SKU
    barcode_height = min(10 * mm, height / 4)
    barcode = code128.Code128(context.sku, barHeight=barcode_height, barWidth=0.28)
    max_barcode_width = width - (qr_width + 12 * mm)
    scale_x = 1.0
    try:
        if barcode.width > max_barcode_width:
            scale_x = max(0.45, float(max_barcode_width) / float(barcode.width))
    except Exception:
        scale_x = 1.0
    c.saveState()
    c.translate(5 * mm, 5 * mm)
    c.scale(scale_x, 1.0)
    barcode.drawOn(c, 0, 0)
    c.restoreState()

    # Pie con sucursal
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#94a3b8"))
    c.drawRightString(width - 5 * mm, height - 7 * mm, context.store_name[:32])

    c.showPage()
    c.save()

    buffer.seek(0)
    filename = f"etiqueta_{store_id}_{context.sku}.pdf"
    return buffer.getvalue(), filename


def render_device_label_commands(
    db: Session,
    store_id: int,
    device_id: int,
    *,
    format: schemas.LabelFormat,
    template_key: schemas.LabelTemplateKey | None = None,
) -> tuple[str, str]:
    """Genera comandos directos para Zebra o Epson."""

    context, _device = _build_label_context(db, store_id, device_id)
    template = _resolve_template(template_key)
    filename_suffix = "zpl" if format is schemas.LabelFormat.ZPL else "txt"

    if format is schemas.LabelFormat.ZPL:
        dots_per_mm = 8  # 203 dpi
        width_dots = int(template.width_mm * dots_per_mm)
        height_dots = int(template.height_mm * dots_per_mm)
        lines = [
            "^XA",
            f"^PW{width_dots}",
            f"^LL{height_dots}",
            "^CI28",
            "^CF0,28",
            f"^FO24,{height_dots - 90}^FD{context.name[:38]}^FS",
            f"^CF0,22^FO24,{height_dots - 120}^FDSKU: {context.sku}^FS",
            f"^CF0,28^FO24,{height_dots - 150}^FDPrecio: {context.price_text}^FS",
        ]
        text_y = height_dots - 180
        for identifier_line in context.identifiers[:4]:
            lines.append(f"^CF0,20^FO24,{text_y}^FD{identifier_line}^FS")
            text_y -= 26
        if context.spec_line:
            lines.append(f"^CF0,20^FO24,{max(40, text_y)}^FD{context.spec_line[:64]}^FS")
        lines.extend(
            [
                f"^BQN,2,4^FO{width_dots - 120},24^FDQA,{context.qr_data}^FS",
                f"^BY2,2,60^FO24,24^BCN,60,Y,N,N^FD{context.sku}^FS",
                "^XZ",
            ]
        )
        commands = "\n".join(lines)
    else:
        commands_lines = [
            "\x1b@",  # Reset
            "\x1b!0",  # Fuente normal
            f"{context.name[:38]}\n",
            f"SKU: {context.sku}\n",
            f"Precio: {context.price_text}\n",
        ]
        for identifier_line in context.identifiers[:4]:
            commands_lines.append(f"{identifier_line}\n")
        if context.spec_line:
            commands_lines.append(f"{context.spec_line}\n")
        commands_lines.extend(
            [
                "\x1dL",  # Densidad
                f"QR:{context.qr_data}\n",
                f"BARCODE:{context.sku}\n",
                "\x1di\x42",  # Corte parcial si aplica
            ]
        )
        commands = "".join(commands_lines)

    filename = f"etiqueta_{store_id}_{context.sku}.{filename_suffix}"
    return commands, filename
