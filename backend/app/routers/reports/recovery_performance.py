"""Contratos de reportes perdidos durante la división del router monolítico.

REC-0004 restaura aquí únicamente endpoints que existían en ``reports.py`` y
que siguen siendo consumidos por tests/frontend. Debe eliminarse al completar
la migración definitiva a módulos especializados.
"""
from __future__ import annotations

import csv
from datetime import date, datetime
from io import BytesIO, StringIO
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app import crud, schemas
from backend.app.core.roles import ADMIN, REPORTE_ROLES
from backend.app.database import get_db
from backend.app.routers.dependencies import require_reason, require_reason_optional
from backend.app.security import require_roles
from backend.app.services import performance_reports
from .common import ensure_analytics_enabled, normalize_sales_range

router = APIRouter(tags=["reportes"])


@router.get("/analytics/export.csv", response_model=schemas.BinaryFileResponse)
def analytics_export_csv(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    supplier: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    ensure_analytics_enabled()
    kwargs = dict(
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=200,
        offset=0,
    )
    comparatives = crud.calculate_store_comparatives(db, **kwargs)
    profit = crud.calculate_profit_margin(db, **kwargs)
    projection = crud.calculate_sales_projection(db, **kwargs)

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Comparativo sucursales"])
    writer.writerow([
        "Sucursal", "Dispositivos", "Unidades", "Valor inventario",
        "Rotación promedio", "Envejecimiento promedio", "Ventas 30d", "Órdenes 30d",
    ])
    for item in comparatives:
        writer.writerow([
            item["store_name"], item["device_count"], item["total_units"],
            f"{item['inventory_value']:.2f}", f"{item['average_rotation']:.2f}",
            f"{item['average_aging_days']:.2f}", f"{item['sales_last_30_days']:.2f}",
            item["sales_count_last_30_days"],
        ])

    writer.writerow([])
    writer.writerow(["Margen por sucursal"])
    writer.writerow(["Sucursal", "Ingresos", "Costo", "Utilidad", "% Margen"])
    for item in profit:
        writer.writerow([
            item["store_name"], f"{item['revenue']:.2f}", f"{item['cost']:.2f}",
            f"{item['profit']:.2f}", f"{item['margin_percent']:.2f}",
        ])

    writer.writerow([])
    writer.writerow(["Proyección ventas 30 días"])
    writer.writerow([
        "Sucursal", "Unidades diarias", "Ticket promedio", "Unidades proyectadas",
        "Ingresos proyectados", "Confianza",
    ])
    for item in projection:
        writer.writerow([
            item["store_name"], f"{item['average_daily_units']:.2f}",
            f"{item['average_ticket']:.2f}", f"{item['projected_units']:.2f}",
            f"{item['projected_revenue']:.2f}", f"{item['confidence']:.2f}",
        ])

    metadata = schemas.BinaryFileResponse(
        filename="softmobile_analytics.csv", media_type="text/csv"
    )
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


def _performance_inputs(
    db: Session,
    *,
    store_ids: list[int] | None,
    date_from: datetime | date | None,
    date_to: datetime | date | None,
    category: str | None,
    supplier: str | None,
):
    normalized_from, normalized_to = normalize_sales_range(date_from, date_to)
    kwargs = dict(
        store_ids=store_ids,
        date_from=normalized_from,
        date_to=normalized_to,
        category=category,
        supplier=supplier,
    )
    return (
        normalized_from,
        normalized_to,
        crud.calculate_rotation_analytics(db, **kwargs),
        crud.calculate_profit_margin(db, **kwargs),
        crud.calculate_sales_by_store(db, **kwargs),
        crud.calculate_sales_by_category(db, **kwargs),
        crud.calculate_sales_timeseries(db, **kwargs),
    )


@router.get("/financial", response_model=schemas.FinancialPerformanceReport)
def financial_report(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    supplier: str | None = Query(default=None, min_length=1, max_length=120),
    format: Literal["json", "pdf", "xlsx"] = Query(default="json"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
    reason: str | None = Depends(require_reason_optional),
):
    ensure_analytics_enabled()
    (
        normalized_from,
        normalized_to,
        rotation,
        profit_by_store,
        sales_by_store,
        sales_by_category,
        sales_trend,
    ) = _performance_inputs(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
    )

    total_revenue = sum(item["revenue"] for item in profit_by_store)
    total_cost = sum(item["cost"] for item in profit_by_store)
    total_profit = sum(item["profit"] for item in profit_by_store)
    total_margin = round(total_profit / total_revenue * 100, 2) if total_revenue else 0.0
    filters = schemas.ReportFilterState(
        date_from=normalized_from,
        date_to=normalized_to,
        store_ids=store_ids or [],
        category=category,
    )
    report = schemas.FinancialPerformanceReport(
        generated_at=datetime.utcnow(),
        filters=filters,
        rotation=[schemas.RotationMetric.model_validate(item).model_dump() for item in rotation],
        profit_by_store=[schemas.ProfitMarginMetric.model_validate(item).model_dump() for item in profit_by_store],
        sales_by_store=[schemas.SalesByStoreMetric.model_validate(item).model_dump() for item in sales_by_store],
        sales_by_category=[schemas.SalesByCategoryMetric.model_validate(item).model_dump() for item in sales_by_category],
        sales_trend=[schemas.SalesTimeseriesPoint.model_validate(item).model_dump() for item in sales_trend],
        totals=schemas.FinancialTotals(
            revenue=total_revenue,
            cost=total_cost,
            profit=total_profit,
            margin_percent=total_margin,
        ),
    )
    if format in {"pdf", "xlsx"} and not reason:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reason header requerido")
    if format == "pdf":
        pdf_bytes = performance_reports.render_financial_report_pdf(report)
        metadata = schemas.BinaryFileResponse(
            filename="softmobile_reporte_financiero.pdf", media_type="application/pdf"
        )
        return StreamingResponse(
            BytesIO(pdf_bytes), media_type=metadata.media_type, headers=metadata.content_disposition()
        )
    if format == "xlsx":
        workbook = performance_reports.render_financial_report_xlsx(report)
        metadata = schemas.BinaryFileResponse(
            filename="softmobile_reporte_financiero.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        return StreamingResponse(
            workbook, media_type=metadata.media_type, headers=metadata.content_disposition()
        )
    return report


@router.get("/inventory", response_model=schemas.InventoryPerformanceReport)
def inventory_performance_report(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    supplier: str | None = Query(default=None, min_length=1, max_length=120),
    format: Literal["json", "pdf", "xlsx"] = Query(default="json"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
    reason: str | None = Depends(require_reason_optional),
):
    ensure_analytics_enabled()
    (
        normalized_from,
        normalized_to,
        rotation,
        profit_by_store,
        sales_by_store,
        sales_by_category,
        sales_trend,
    ) = _performance_inputs(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
    )
    report = schemas.InventoryPerformanceReport(
        generated_at=datetime.utcnow(),
        filters=schemas.ReportFilterState(
            date_from=normalized_from,
            date_to=normalized_to,
            store_ids=store_ids or [],
            category=category,
        ),
        rotation=[schemas.RotationMetric.model_validate(item).model_dump() for item in rotation],
        profit_by_store=[schemas.ProfitMarginMetric.model_validate(item).model_dump() for item in profit_by_store],
        sales_by_store=[schemas.SalesByStoreMetric.model_validate(item).model_dump() for item in sales_by_store],
        sales_by_category=[schemas.SalesByCategoryMetric.model_validate(item).model_dump() for item in sales_by_category],
        sales_trend=[schemas.SalesTimeseriesPoint.model_validate(item).model_dump() for item in sales_trend],
    )
    if format in {"pdf", "xlsx"} and not reason:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reason header requerido")
    if format == "pdf":
        pdf_bytes = performance_reports.render_inventory_report_pdf(report)
        metadata = schemas.BinaryFileResponse(
            filename="softmobile_reporte_inventario.pdf", media_type="application/pdf"
        )
        return StreamingResponse(
            BytesIO(pdf_bytes), media_type=metadata.media_type, headers=metadata.content_disposition()
        )
    if format == "xlsx":
        workbook = performance_reports.render_inventory_report_xlsx(report)
        metadata = schemas.BinaryFileResponse(
            filename="softmobile_reporte_inventario.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        return StreamingResponse(
            workbook, media_type=metadata.media_type, headers=metadata.content_disposition()
        )
    return report


__all__ = ["router"]
