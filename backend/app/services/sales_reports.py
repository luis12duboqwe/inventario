"""Utilidades para generar reportes de ventas en PDF y Excel."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .. import models, schemas


def _format_currency(value: Decimal | float | int) -> str:
    normalized = float(value)
    return f"${normalized:,.2f}"


def _build_pdf_table(data: list[list[str]]) -> Table:
    table = Table(data, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#e2e8f0")),
                ("LINEABOVE", (0, 0), (-1, 0), 1, colors.HexColor("#38bdf8")),
                ("LINEBELOW", (0, -1), (-1, -1), 1, colors.HexColor("#38bdf8")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ]
        )
    )
    return table


def _build_pdf_document(title: str) -> tuple[list, SimpleDocTemplate, BytesIO]:  # type: ignore[type-arg]
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, title=title)
    styles = getSampleStyleSheet()
    now_label = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")

    heading_style = ParagraphStyle(
        "Heading1Softmobile",
        parent=styles["Heading1"],
        textColor=colors.HexColor("#38bdf8"),
    )

    elements: list = [  # type: ignore[var-annotated]
        Paragraph("Softmobile 2025 — Reporte de ventas", heading_style),
        Spacer(1, 12),
        Paragraph(f"Generado automáticamente el {now_label}", styles["Normal"]),
        Spacer(1, 18),
    ]

    return elements, document, buffer


def build_sales_report(
    sales: list[models.Sale],
    filters: schemas.SalesReportFilters,
) -> schemas.SalesReport:
    subtotal_total = Decimal("0")
    tax_total = Decimal("0")
    total_amount = Decimal("0")
    daily_totals: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
    report_items: list[schemas.SalesReportItem] = []

    for sale in sales:
        subtotal_total += sale.subtotal_amount
        tax_total += sale.tax_amount
        total_amount += sale.total_amount
        sale_day = sale.created_at.date()
        daily_totals[sale_day] += sale.total_amount

        customer_name = sale.customer_name or sale.customer.name if sale.customer else None
        performed_by = None
        if sale.performed_by:
            performed_by = sale.performed_by.full_name or sale.performed_by.username

        folio = f"VENTA-{sale.id:06d}"
        if sale.store and getattr(sale.store, "name", None):
            prefix = sale.store.name.strip().upper()[:4].replace(" ", "")
            if prefix:
                folio = f"{prefix}-{sale.id:06d}"

        item_models = [
            schemas.SaleItemResponse.model_validate(item, from_attributes=True)
            for item in sale.items
        ]

        report_items.append(
            schemas.SalesReportItem(
                sale_id=sale.id,
                folio=folio,
                store_name=sale.store.name if sale.store else f"Sucursal #{sale.store_id}",
                customer_name=customer_name,
                performed_by=performed_by,
                payment_method=sale.payment_method,
                subtotal=sale.subtotal_amount,
                tax=sale.tax_amount,
                total=sale.total_amount,
                created_at=sale.created_at,
                items=item_models,
            )
        )

    daily_stats = [
        schemas.DashboardChartPoint(label=day.strftime("%d/%m/%Y"), value=float(amount))
        for day, amount in sorted(daily_totals.items())
    ]

    totals = schemas.SalesReportTotals(
        count=len(sales),
        subtotal=subtotal_total,
        tax=tax_total,
        total=total_amount,
    )

    return schemas.SalesReport(
        generated_at=datetime.utcnow(),
        filters=filters,
        totals=totals,
        daily_stats=daily_stats,
        items=report_items,
    )


def render_sales_report_pdf(report: schemas.SalesReport) -> bytes:
    elements, document, buffer = _build_pdf_document("Softmobile - Reporte de ventas")
    styles = getSampleStyleSheet()

    filters_parts: list[str] = []
    if report.filters.store_id:
        filters_parts.append(f"Sucursal #{report.filters.store_id}")
    if report.filters.customer_id:
        filters_parts.append(f"Cliente #{report.filters.customer_id}")
    if report.filters.performed_by_id:
        filters_parts.append(f"Usuario #{report.filters.performed_by_id}")
    if report.filters.date_from or report.filters.date_to:
        start = report.filters.date_from.strftime("%d/%m/%Y") if report.filters.date_from else "∞"
        end = report.filters.date_to.strftime("%d/%m/%Y") if report.filters.date_to else "∞"
        filters_parts.append(f"Periodo: {start} → {end}")
    if report.filters.query:
        filters_parts.append(f"Búsqueda: {report.filters.query}")

    filters_text = ", ".join(filters_parts) if filters_parts else "Sin filtros aplicados"
    elements.append(Paragraph(filters_text, styles["Italic"]))
    elements.append(Spacer(1, 12))

    summary_table = _build_pdf_table(
        [
            ["Indicador", "Valor"],
            ["Operaciones", str(report.totals.count)],
            ["Subtotal", _format_currency(report.totals.subtotal)],
            ["Impuestos", _format_currency(report.totals.tax)],
            ["Total", _format_currency(report.totals.total)],
        ]
    )
    elements.append(summary_table)
    elements.append(Spacer(1, 18))

    detail_table: list[list[str]] = [
        [
            "Folio",
            "Fecha",
            "Sucursal",
            "Cliente",
            "Total",
            "Impuesto",
            "Método",
            "Usuario",
        ]
    ]

    for item in report.items:
        detail_table.append(
            [
                item.folio,
                item.created_at.strftime("%d/%m/%Y %H:%M"),
                item.store_name,
                item.customer_name or "Mostrador",
                _format_currency(item.total),
                _format_currency(item.tax),
                item.payment_method.value,
                item.performed_by or "—",
            ]
        )

    elements.append(_build_pdf_table(detail_table))

    if report.daily_stats:
        elements.append(Spacer(1, 18))
        elements.append(Paragraph("Ventas por día", styles["Heading3"]))
        daily_table = _build_pdf_table(
            [["Día", "Total"]]
            + [[entry.label, _format_currency(entry.value)] for entry in report.daily_stats]
        )
        elements.append(daily_table)

    document.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def render_sales_report_excel(report: schemas.SalesReport) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Ventas"

    header_fill = PatternFill("solid", fgColor="0f172a")
    header_font = Font(color="FFFFFF", bold=True)

    sheet.append(["Resumen", "Valor"])
    sheet.cell(row=1, column=1).fill = header_fill
    sheet.cell(row=1, column=2).fill = header_fill
    sheet.cell(row=1, column=1).font = header_font
    sheet.cell(row=1, column=2).font = header_font

    summary_rows = [
        ("Operaciones", report.totals.count),
        ("Subtotal", _format_currency(report.totals.subtotal)),
        ("Impuestos", _format_currency(report.totals.tax)),
        ("Total", _format_currency(report.totals.total)),
    ]
    for label, value in summary_rows:
        sheet.append([label, value])

    sheet.append([])
    detail_headers = [
        "Folio",
        "Fecha",
        "Sucursal",
        "Cliente",
        "Total",
        "Impuesto",
        "Método",
        "Usuario",
    ]
    header_row = sheet.max_row + 1
    sheet.append(detail_headers)
    for col_idx, _ in enumerate(detail_headers, start=1):
        cell = sheet.cell(row=header_row, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="left")

    for item in report.items:
        sheet.append(
            [
                item.folio,
                item.created_at.strftime("%d/%m/%Y %H:%M"),
                item.store_name,
                item.customer_name or "Mostrador",
                _format_currency(item.total),
                _format_currency(item.tax),
                item.payment_method.value,
                item.performed_by or "—",
            ]
        )

    for column in range(1, sheet.max_column + 1):
        column_letter = get_column_letter(column)
        sheet.column_dimensions[column_letter].width = 18

    daily_sheet = workbook.create_sheet("Diario")
    daily_sheet.append(["Día", "Total"])
    for cell in daily_sheet[1]:
        cell.fill = header_fill
        cell.font = header_font
    for entry in report.daily_stats:
        daily_sheet.append([entry.label, _format_currency(entry.value)])
    for column in range(1, daily_sheet.max_column + 1):
        column_letter = get_column_letter(column)
        daily_sheet.column_dimensions[column_letter].width = 20

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output.getvalue()
