"""Exportaciones avanzadas del catálogo de dispositivos (PDF y Excel).

Complementa `inventory_import.export_devices_csv` con formatos adicionales
sin romper compatibilidad v2.2.0. No modifica rutas existentes: se agregan
endpoints nuevos para PDF y XLSX.
"""
from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Iterable

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from .. import crud, models

PDF_HEADER_FIELDS = [
    "SKU",
    "Nombre",
    "Marca",
    "Modelo",
    "Cant",
    "Precio",
    "IMEI/Serial",
]

EXCEL_HEADERS = [
    "sku",
    "name",
    "marca",
    "modelo",
    "quantity",
    "unit_price",
    "imei",
    "serial",
]


def _fetch_devices(
    db: Session,
    store_id: int,
    *,
    search: str | None,
    estado: models.CommercialState | None,
    categoria: str | None,
    condicion: str | None,
    estado_inventario: str | None,
    ubicacion: str | None,
    proveedor: str | None,
    fecha_ingreso_desde: datetime | None,
    fecha_ingreso_hasta: datetime | None,
) -> Iterable[models.Device]:
    return crud.list_devices(
        db,
        store_id,
        search=search,
        estado=estado,
        categoria=categoria,
        condicion=condicion,
        estado_inventario=estado_inventario,
        ubicacion=ubicacion,
        proveedor=proveedor,
        fecha_ingreso_desde=fecha_ingreso_desde,
        fecha_ingreso_hasta=fecha_ingreso_hasta,
        limit=None,
    )


def render_devices_catalog_pdf(
    db: Session,
    store_id: int,
    *,
    search: str | None = None,
    estado: models.CommercialState | None = None,
    categoria: str | None = None,
    condicion: str | None = None,
    estado_inventario: str | None = None,
    ubicacion: str | None = None,
    proveedor: str | None = None,
    fecha_ingreso_desde: datetime | None = None,
    fecha_ingreso_hasta: datetime | None = None,
) -> bytes:
    """Genera un PDF del catálogo filtrado en diseño simple compatible."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin_x = 36
    y = height - 48
    # Encabezado
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin_x, y, f"Catálogo dispositivos — Sucursal {store_id}")
    y -= 18
    c.setFont("Helvetica", 9)
    generated = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    c.drawString(margin_x, y, f"Generado: {generated}")
    y -= 22
    # Cabecera de tabla
    c.setFont("Helvetica-Bold", 8)
    for idx, header in enumerate(PDF_HEADER_FIELDS):
        c.drawString(margin_x + idx * 70, y, header)
    y -= 12
    c.setFont("Helvetica", 7)

    devices = _fetch_devices(
        db,
        store_id,
        search=search,
        estado=estado,
        categoria=categoria,
        condicion=condicion,
        estado_inventario=estado_inventario,
        ubicacion=ubicacion,
        proveedor=proveedor,
        fecha_ingreso_desde=fecha_ingreso_desde,
        fecha_ingreso_hasta=fecha_ingreso_hasta,
    )
    for device in devices:
        row_values = [
            device.sku,
            (device.name or "")[:26],
            (device.marca or "")[:14],
            (device.modelo or "")[:16],
            str(device.quantity),
            f"{device.unit_price:.2f}" if device.unit_price else "0.00",
            (device.imei or device.serial or "")[:17],
        ]
        for idx, value in enumerate(row_values):
            c.drawString(margin_x + idx * 70, y, value)
        y -= 11
        if y < 54:  # salto de página
            c.showPage()
            y = height - 48
            c.setFont("Helvetica-Bold", 8)
            for idx, header in enumerate(PDF_HEADER_FIELDS):
                c.drawString(margin_x + idx * 70, y, header)
            y -= 12
            c.setFont("Helvetica", 7)
    c.showPage()
    c.save()
    return buffer.getvalue()


def render_devices_catalog_excel(
    db: Session,
    store_id: int,
    *,
    search: str | None = None,
    estado: models.CommercialState | None = None,
    categoria: str | None = None,
    condicion: str | None = None,
    estado_inventario: str | None = None,
    ubicacion: str | None = None,
    proveedor: str | None = None,
    fecha_ingreso_desde: datetime | None = None,
    fecha_ingreso_hasta: datetime | None = None,
) -> bytes:
    """Genera un XLSX del catálogo filtrado."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Catalogo"
    ws.append(EXCEL_HEADERS)
    devices = _fetch_devices(
        db,
        store_id,
        search=search,
        estado=estado,
        categoria=categoria,
        condicion=condicion,
        estado_inventario=estado_inventario,
        ubicacion=ubicacion,
        proveedor=proveedor,
        fecha_ingreso_desde=fecha_ingreso_desde,
        fecha_ingreso_hasta=fecha_ingreso_hasta,
    )
    for device in devices:
        ws.append(
            [
                device.sku,
                device.name,
                device.marca,
                device.modelo,
                device.quantity,
                float(device.unit_price or 0),
                device.imei,
                device.serial,
            ]
        )
    stream = BytesIO()
    wb.save(stream)
    return stream.getvalue()


__all__ = ["render_devices_catalog_pdf", "render_devices_catalog_excel"]
