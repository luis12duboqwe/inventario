"""Servicios de generación de reportes y respaldos empresariales."""
from __future__ import annotations

import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Tuple
from zipfile import ZIP_DEFLATED, ZipFile

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from .. import crud, models


def build_inventory_snapshot(db: Session) -> dict[str, Any]:
    """Obtiene un snapshot completo de los datos de inventario."""

    return crud.build_inventory_snapshot(db)

def _build_financial_table(devices: list[dict[str, Any]]) -> Tuple[list[list[str]], float]:
    table_data = [
        [
            "SKU",
            "Nombre",
            "Cantidad",
            "Precio",
            "Valor total",
            "IMEI",
            "Serie",
            "Marca",
            "Modelo",
            "Proveedor",
        ]
    ]
    store_total = 0.0
    for device in devices:
        unit_price = float(device.get("unit_price", 0.0))
        total_value = float(device.get("inventory_value", device["quantity"] * unit_price))
        store_total += total_value
        table_data.append(
            [
                device["sku"],
                device["name"],
                str(device["quantity"]),
                f"${unit_price:,.2f}",
                f"${total_value:,.2f}",
                device.get("imei") or "-",
                device.get("serial") or "-",
                device.get("marca") or "-",
                device.get("modelo") or "-",
                device.get("proveedor") or "-",
            ]
        )

    return table_data, store_total


def _build_catalog_detail_table(devices: list[dict[str, Any]]) -> list[list[str]]:
    detail_table_data = [
        [
            "SKU",
            "Color",
            "Capacidad (GB)",
            "Estado",
            "Lote",
            "Fecha compra",
            "Garantía (meses)",
            "Costo unitario",
            "Margen (%)",
        ]
    ]

    for device in devices:
        capacidad = device.get("capacidad_gb")
        detail_table_data.append(
            [
                device["sku"],
                device.get("color") or "-",
                str(capacidad) if capacidad is not None else "-",
                device.get("estado_comercial", "-"),
                device.get("lote") or "-",
                device.get("fecha_compra") or "-",
                str(device.get("garantia_meses", "-")),
                f"${float(device.get('costo_unitario', 0.0)):,.2f}",
                f"{float(device.get('margen_porcentaje', 0.0)):.2f}%",
            ]
        )

    return detail_table_data


def render_snapshot_pdf(snapshot: dict[str, Any]) -> bytes:
    """Construye un PDF en tema oscuro con el estado del inventario."""

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="Softmobile - Inventario Consolidado")
    styles = getSampleStyleSheet()

    elements = [Paragraph("Softmobile 2025 — Reporte Empresarial", styles["Title"]), Spacer(1, 12)]
    generated_at = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")
    elements.append(Paragraph(f"Generado automáticamente el {generated_at}", styles["Normal"]))
    elements.append(Spacer(1, 18))

    consolidated_total = 0.0

    for store in snapshot.get("stores", []):
        elements.append(Paragraph(f"Sucursal: {store['name']} ({store['timezone']})", styles["Heading2"]))
        if store.get("location"):
            elements.append(Paragraph(f"Ubicación: {store['location']}", styles["Normal"]))
        devices = store.get("devices", [])
        if not devices:
            elements.append(Paragraph("Sin dispositivos registrados", styles["Italic"]))
            elements.append(Spacer(1, 12))
            continue

        table_data, store_total = _build_financial_table(devices)

        registered_value_raw = store.get("inventory_value")
        try:
            registered_value = float(registered_value_raw) if registered_value_raw is not None else None
        except (TypeError, ValueError):
            registered_value = None

        elements.append(
            Paragraph(
                f"Valor calculado (sumatoria de dispositivos): ${store_total:,.2f}",
                styles["Normal"],
            )
        )
        if registered_value is not None:
            elements.append(
                Paragraph(
                    f"Valor registrado en sucursal: ${registered_value:,.2f}",
                    styles["Normal"],
                )
            )
        elements.append(Spacer(1, 6))
        table = Table(table_data, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#1e293b")),
                    ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#e2e8f0")),
                    ("LINEABOVE", (0, 0), (-1, 0), 1, colors.HexColor("#38bdf8")),
                    ("LINEBELOW", (0, -1), (-1, -1), 1, colors.HexColor("#38bdf8")),
                    ("ALIGN", (2, 1), (4, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ]
            )
        )
        elements.append(table)
        elements.append(Spacer(1, 12))

        detail_table_data = _build_catalog_detail_table(devices)

        detail_table = Table(detail_table_data, hAlign="LEFT")
        detail_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#111827")),
                    ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#cbd5f5")),
                    ("LINEABOVE", (0, 0), (-1, 0), 1, colors.HexColor("#38bdf8")),
                    ("LINEBELOW", (0, -1), (-1, -1), 1, colors.HexColor("#38bdf8")),
                    ("ALIGN", (2, 1), (2, -1), "CENTER"),
                    ("ALIGN", (4, 1), (5, -1), "CENTER"),
                    ("ALIGN", (6, 1), (8, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ]
            )
        )
        elements.append(detail_table)
        elements.append(Spacer(1, 18))

        consolidated_total += store_total

    summary = snapshot.get("summary") or {}
    if summary:
        summary_value_raw = summary.get("inventory_value")
        try:
            summary_value = float(summary_value_raw) if summary_value_raw is not None else 0.0
        except (TypeError, ValueError):
            summary_value = 0.0

        elements.append(Paragraph("Resumen corporativo", styles["Heading2"]))
        elements.append(Paragraph(f"Sucursales auditadas: {summary.get('store_count', 0)}", styles["Normal"]))
        elements.append(
            Paragraph(
                f"Dispositivos catalogados: {summary.get('device_records', 0)}",
                styles["Normal"],
            )
        )
        elements.append(
            Paragraph(
                f"Unidades totales en inventario: {summary.get('total_units', 0)}",
                styles["Normal"],
            )
        )
        elements.append(
            Paragraph(
                f"Inventario consolidado registrado: ${summary_value:,.2f}",
                styles["Normal"],
            )
        )
        elements.append(
            Paragraph(
                f"Inventario consolidado calculado: ${consolidated_total:,.2f}",
                styles["Normal"],
            )
        )
        elements.append(Spacer(1, 18))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


def serialize_snapshot(snapshot: dict[str, Any]) -> bytes:
    """Serializa el snapshot en formato JSON."""

    return json.dumps(snapshot, ensure_ascii=False, indent=2).encode("utf-8")


def generate_backup(
    db: Session,
    *,
    base_dir: str,
    mode: models.BackupMode,
    triggered_by_id: int | None,
    notes: str | None = None,
) -> models.BackupJob:
    """Genera los archivos de respaldo y persiste el registro en la base."""

    snapshot = build_inventory_snapshot(db)
    pdf_bytes = render_snapshot_pdf(snapshot)
    json_bytes = serialize_snapshot(snapshot)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    directory = Path(base_dir)
    directory.mkdir(parents=True, exist_ok=True)

    pdf_path = directory / f"softmobile_inventario_{timestamp}.pdf"
    archive_path = directory / f"softmobile_respaldo_{timestamp}.zip"

    pdf_path.write_bytes(pdf_bytes)
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as zip_file:
        zip_file.writestr(f"snapshot_{timestamp}.json", json_bytes)

    total_size = pdf_path.stat().st_size + archive_path.stat().st_size

    job = crud.create_backup_job(
        db,
        mode=mode,
        pdf_path=str(pdf_path.resolve()),
        archive_path=str(archive_path.resolve()),
        total_size_bytes=total_size,
        notes=notes,
        triggered_by_id=triggered_by_id,
    )
    return job
