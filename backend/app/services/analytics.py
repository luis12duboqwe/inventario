"""Servicios para construir reportes analíticos avanzados."""
from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart


def _build_bar_chart(title: str, values: list[float], labels: list[str]) -> Drawing:
    drawing = Drawing(400, 200)
    chart = VerticalBarChart()
    chart.data = [values]
    chart.categoryAxis.categoryNames = labels
    chart.barWidth = 1 * cm
    chart.barSpacing = 0.3 * cm
    chart.valueAxis.valueMin = 0
    chart.fillColor = colors.HexColor("#0f172a")
    chart.strokeColor = colors.HexColor("#38bdf8")
    chart.bars[0].fillColor = colors.HexColor("#38bdf8")
    chart.valueAxis.strokeColor = colors.HexColor("#38bdf8")
    chart.categoryAxis.strokeColor = colors.HexColor("#38bdf8")
    chart.categoryAxis.labels.fillColor = colors.HexColor("#e2e8f0")
    chart.valueAxis.labels.fillColor = colors.HexColor("#e2e8f0")
    chart.width = 360
    chart.height = 140
    title_label = String(0, chart.height + 20, title, fontName="Helvetica-Bold", fontSize=12, fillColor=colors.HexColor("#38bdf8"))
    drawing.add(chart)
    drawing.add(title_label)
    return drawing


def _build_line_chart(title: str, values: list[float], labels: list[str]) -> Drawing:
    drawing = Drawing(400, 200)
    chart = HorizontalLineChart()
    chart.data = [values]
    chart.categoryAxis.categoryNames = labels
    chart.strokeColor = colors.HexColor("#38bdf8")
    chart.lines[0].strokeColor = colors.HexColor("#38bdf8")
    chart.categoryAxis.labels.fillColor = colors.HexColor("#e2e8f0")
    chart.valueAxis.labels.fillColor = colors.HexColor("#e2e8f0")
    chart.valueAxis.valueMin = 0
    chart.width = 360
    chart.height = 140
    title_label = String(0, chart.height + 20, title, fontName="Helvetica-Bold", fontSize=12, fillColor=colors.HexColor("#38bdf8"))
    drawing.add(chart)
    drawing.add(title_label)
    return drawing


def render_analytics_pdf(
    *,
    rotation: list[dict[str, Any]],
    aging: list[dict[str, Any]],
    forecast: list[dict[str, Any]],
    comparatives: list[dict[str, Any]] | None = None,
    profit: list[dict[str, Any]] | None = None,
    projection: list[dict[str, Any]] | None = None,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="Softmobile - Analítica avanzada")
    styles = getSampleStyleSheet()
    dark_style = ParagraphStyle(
        name="DarkBody",
        parent=styles["BodyText"],
        textColor=colors.HexColor("#e2e8f0"),
        backColor=colors.HexColor("#0f172a"),
        borderWidth=0,
    )

    comparatives = comparatives or []
    profit = profit or []
    projection = projection or []

    elements = [
        Paragraph("Softmobile 2025 — Analítica avanzada", styles["Title"]),
        Spacer(1, 12),
        Paragraph("Resumen rotación top dispositivos", dark_style),
    ]

    top_rotation = rotation[:5]
    if top_rotation:
        labels = [item["sku"] for item in top_rotation]
        values = [float(item["rotation_rate"]) for item in top_rotation]
        elements.append(_build_bar_chart("Rotación (top 5)", values, labels))
    else:
        elements.append(Paragraph("Sin datos de ventas", dark_style))

    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Envejecimiento de inventario", dark_style))
    top_aging = aging[:5]
    if top_aging:
        labels = [item["sku"] for item in top_aging]
        values = [float(item["days_in_stock"]) for item in top_aging]
        elements.append(_build_bar_chart("Días en inventario", values, labels))
    else:
        elements.append(Paragraph("Sin datos de envejecimiento", dark_style))

    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Pronóstico de agotamiento", dark_style))
    top_forecast = forecast[:5]
    if top_forecast:
        labels = [item["sku"] for item in top_forecast]
        values = [float(item["projected_days"] or 0) for item in top_forecast]
        elements.append(_build_line_chart("Días proyectados", values, labels))
    else:
        elements.append(Paragraph("Sin datos de pronóstico", dark_style))

    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Comparativo de sucursales", dark_style))
    if comparatives:
        comp_lines = "<br/>".join(
            f"<b>{item['store_name']}</b>: inventario ${item['inventory_value']:.2f} · rotación {item['average_rotation']:.2f} · ventas 30d ${item['sales_last_30_days']:.2f}"
            for item in comparatives[:5]
        )
        elements.append(Paragraph(comp_lines, dark_style))
    else:
        elements.append(Paragraph("Sin comparativos disponibles", dark_style))

    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Margen de contribución", dark_style))
    if profit:
        profit_lines = "<br/>".join(
            f"<b>{item['store_name']}</b>: margen {item['margin_percent']:.2f}% (${item['profit']:.2f})"
            for item in profit[:5]
        )
        elements.append(Paragraph(profit_lines, dark_style))
    else:
        elements.append(Paragraph("Sin registros de ventas consolidados", dark_style))

    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Proyección de ventas (30 días)", dark_style))
    if projection:
        projection_lines = "<br/>".join(
            f"<b>{item['store_name']}</b>: unidades {item['projected_units']:.1f} · ticket promedio ${item['average_ticket']:.2f} · ingreso esperado ${item['projected_revenue']:.2f}"
            for item in projection[:5]
        )
        elements.append(Paragraph(projection_lines, dark_style))
    else:
        elements.append(Paragraph("Sin suficientes datos para proyectar ventas", dark_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
