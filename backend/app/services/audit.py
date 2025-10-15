"""Servicios especializados para reportes y visualizaciones de auditoría."""
from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Iterable, Mapping

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..models import AuditLog
from ..utils import audit as audit_utils


def render_audit_pdf(
    logs: Iterable[AuditLog],
    *,
    filters: Mapping[str, str],
    alerts: audit_utils.AuditAlertSummary,
) -> bytes:
    """Construye un PDF en tema oscuro con filtros y alertas visibles."""

    logs = list(logs)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="Softmobile - Auditoría consolidada")
    styles = getSampleStyleSheet()
    dark_body = ParagraphStyle(
        name="AuditBody",
        parent=styles["BodyText"],
        textColor=colors.HexColor("#e2e8f0"),
        backColor=colors.HexColor("#0f172a"),
        leading=14,
    )
    elements: list = [
        Paragraph("Softmobile 2025 — Bitácora de auditoría", styles["Title"]),
        Spacer(1, 10),
        Paragraph(
            f"Generado el {datetime.utcnow().strftime('%d/%m/%Y %H:%M UTC')}",
            dark_body,
        ),
        Spacer(1, 16),
    ]

    if filters:
        filter_lines = "<br/>".join(
            f"<b>{key}:</b> {value}" for key, value in filters.items()
        )
        elements.extend(
            [
                Paragraph("Filtros aplicados", styles["Heading2"]),
                Paragraph(filter_lines, dark_body),
                Spacer(1, 14),
            ]
        )

    summary_text = (
        "Total de eventos registrados: "
        f"{alerts.total} · Críticos: {alerts.critical} · Preventivos: {alerts.warning} · Informativos: {alerts.info}"
    )
    elements.extend(
        [
            Paragraph("Resumen de alertas", styles["Heading2"]),
            Paragraph(summary_text, dark_body),
        ]
    )

    if alerts.highlights:
        highlights_lines = "<br/>".join(
            f"{entry['created_at'].strftime('%d/%m/%Y %H:%M:%S')} · "
            f"{audit_utils.severity_label(entry['severity'])}: {entry['action']} ({entry['entity_type']})"
            for entry in alerts.highlights
        )
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("Eventos destacados", styles["Heading3"]))
        elements.append(Paragraph(highlights_lines, dark_body))

    elements.append(Spacer(1, 16))

    table_data = [
        ["Fecha", "Acción", "Entidad", "Detalle", "Severidad"],
    ]

    max_rows = 60
    for log in logs[:max_rows]:
        severity = audit_utils.classify_severity(log.action or "", log.details)
        table_data.append(
            [
                log.created_at.strftime("%d/%m/%Y %H:%M:%S"),
                log.action,
                f"{log.entity_type} #{log.entity_id}",
                log.details or "-",
                audit_utils.severity_label(severity),
            ]
        )

    table = Table(table_data, colWidths=[90, 110, 120, 160, 60])
    table_style: list[tuple] = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#111827"), colors.HexColor("#0f172a")]),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#1f2937")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#1f2937")),
    ]

    for idx, log in enumerate(logs[:max_rows], start=1):
        severity = audit_utils.classify_severity(log.action or "", log.details)
        if severity == "critical":
            table_style.append(("BACKGROUND", (0, idx), (-1, idx), colors.HexColor("#451a2d")))
            table_style.append(("TEXTCOLOR", (0, idx), (-1, idx), colors.HexColor("#fecdd3")))
        elif severity == "warning":
            table_style.append(("BACKGROUND", (0, idx), (-1, idx), colors.HexColor("#422006")))
            table_style.append(("TEXTCOLOR", (0, idx), (-1, idx), colors.HexColor("#fde68a")))

    table.setStyle(TableStyle(table_style))
    elements.append(table)

    if len(logs) > max_rows:
        elements.append(Spacer(1, 10))
        elements.append(
            Paragraph(
                f"Nota: se muestran los {max_rows} registros más recientes de {len(logs)} totales.",
                dark_body,
            )
        )

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
