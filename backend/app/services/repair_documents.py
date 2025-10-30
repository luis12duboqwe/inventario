"""Generación de reportes PDF para reparaciones."""

from __future__ import annotations

from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from .. import models


def render_repair_pdf(order: models.RepairOrder) -> bytes:  # // [PACK37-backend]
    """Genera un PDF con el resumen de una orden de reparación."""

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    pdf.setTitle(f"Orden_Reparacion_{order.id}")
    y_position = height - 40

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y_position, f"Orden de reparación #{order.id}")
    y_position -= 20

    pdf.setFont("Helvetica", 11)
    pdf.drawString(40, y_position, f"Sucursal: {order.store_id}")
    y_position -= 14
    pdf.drawString(40, y_position, f"Estado: {order.status.value}")
    y_position -= 14
    if order.customer_name:
        pdf.drawString(40, y_position, f"Cliente: {order.customer_name}")
        y_position -= 14
    if order.customer_contact:
        pdf.drawString(40, y_position, f"Contacto: {order.customer_contact}")
        y_position -= 14
    pdf.drawString(40, y_position, f"Técnico: {order.technician_name}")
    y_position -= 14
    pdf.drawString(40, y_position, f"Daño reportado: {order.damage_type}")
    y_position -= 14
    if order.diagnosis:
        pdf.drawString(40, y_position, "Diagnóstico:")
        y_position -= 12
        pdf.setFont("Helvetica", 10)
        for line in order.diagnosis.splitlines():
            pdf.drawString(60, y_position, line)
            y_position -= 12
        pdf.setFont("Helvetica", 11)
    if order.device_model:
        pdf.drawString(40, y_position, f"Modelo: {order.device_model}")
        y_position -= 14
    if order.imei:
        pdf.drawString(40, y_position, f"IMEI: {order.imei}")
        y_position -= 14
    if order.device_description:
        pdf.drawString(40, y_position, f"Equipo: {order.device_description}")
        y_position -= 14
    if order.notes:
        pdf.drawString(40, y_position, "Notas:")
        y_position -= 12
        pdf.setFont("Helvetica", 10)
        for line in order.notes.splitlines():
            pdf.drawString(60, y_position, line)
            y_position -= 12
        pdf.setFont("Helvetica", 11)

    y_position -= 10
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y_position, "Piezas utilizadas")
    y_position -= 16
    pdf.setFont("Helvetica", 10)
    if not order.parts:
        pdf.drawString(40, y_position, "Sin registros de piezas.")
        y_position -= 14
    else:
        for part in order.parts:
            device_label = None
            if part.device_id and part.device:
                sku = getattr(part.device, "sku", "") or ""
                name = getattr(part.device, "name", "") or ""
                pieces = [value for value in (sku, name) if value]
                device_label = " · ".join(pieces) if pieces else None
            part_label = part.part_name or device_label or f"Repuesto #{part.id}"
            pdf.drawString(40, y_position, f"Repuesto: {part_label}")
            pdf.drawRightString(
                width - 40,
                y_position,
                f"Cantidad: {part.quantity}",
            )
            y_position -= 12
            pdf.drawString(
                60,
                y_position,
                f"Costo unitario: ${float(part.unit_cost):.2f}",
            )
            y_position -= 12
            pdf.drawString(60, y_position, f"Origen: {part.source.value}")
            y_position -= 16
            if y_position < 80:
                pdf.showPage()
                pdf.setFont("Helvetica", 10)
                y_position = height - 60

    if y_position < 120:
        pdf.showPage()
        y_position = height - 60
        pdf.setFont("Helvetica", 11)

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y_position, "Resumen de costos")
    y_position -= 16
    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, y_position, f"Mano de obra: ${float(order.labor_cost):.2f}")
    y_position -= 14
    pdf.drawString(40, y_position, f"Piezas: ${float(order.parts_cost):.2f}")
    y_position -= 14
    pdf.drawString(40, y_position, f"Total: ${float(order.total_cost):.2f}")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()
