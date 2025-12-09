from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app import crud, schemas
from backend.app.core.roles import ADMIN
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.routers.dependencies import require_reason
from backend.app.security import require_roles
from backend.app.services import global_reports_data, global_reports_renderers
from .common import ensure_analytics_enabled, coerce_datetime

router = APIRouter(tags=["reportes"])


@router.get(
    "/global/overview",
    response_model=schemas.GlobalReportOverview
)
def global_report_overview(
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    module: str | None = Query(default=None, max_length=80),
    severity: schemas.SystemLogLevel | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    ensure_analytics_enabled()
    normalized_from = coerce_datetime(date_from)
    normalized_to = coerce_datetime(date_to)
    return global_reports_data.get_overview(
        db,
        date_from=normalized_from,
        date_to=normalized_to,
        module=module,
        severity=severity,
    )


@router.get(
    "/global/dashboard",
    response_model=schemas.GlobalReportDashboard
)
def global_report_dashboard(
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    module: str | None = Query(default=None, max_length=80),
    severity: schemas.SystemLogLevel | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    ensure_analytics_enabled()
    normalized_from = coerce_datetime(date_from)
    normalized_to = coerce_datetime(date_to)
    return global_reports_data.get_dashboard(
        db,
        date_from=normalized_from,
        date_to=normalized_to,
        module=module,
        severity=severity,
    )


@router.get(
    "/global/export",
    response_model=schemas.BinaryFileResponse
)
def export_global_report(
    format: Literal["pdf", "xlsx", "csv"] = Query(default="pdf"),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    module: str | None = Query(default=None, max_length=80),
    severity: schemas.SystemLogLevel | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    normalized_from = coerce_datetime(date_from)
    normalized_to = coerce_datetime(date_to)
    dataset = global_reports_data.build_dataset(
        db,
        date_from=normalized_from,
        date_to=normalized_to,
        module=module,
        severity=severity,
    )
    overview = dataset.overview
    dashboard = dataset.dashboard

    if format == "pdf":
        pdf_bytes = global_reports_renderers.render_global_report_pdf(
            overview, dashboard)
        buffer = BytesIO(pdf_bytes)
        metadata = schemas.BinaryFileResponse(
            filename="softmobile_reporte_global.pdf",
            media_type="application/pdf",
        )
        return StreamingResponse(
            buffer,
            media_type=metadata.media_type,
            headers=metadata.content_disposition(),
        )
    if format == "xlsx":
        workbook = global_reports_renderers.render_global_report_xlsx(
            overview, dashboard)
        metadata = schemas.BinaryFileResponse(
            filename="softmobile_reporte_global.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        return StreamingResponse(
            workbook,
            media_type=metadata.media_type,
            headers=metadata.content_disposition(),
        )
    if format == "csv":
        csv_buffer = global_reports_renderers.render_global_report_csv(
            overview, dashboard)
        metadata = schemas.BinaryFileResponse(
            filename="softmobile_reporte_global.csv",
            media_type="text/csv",
        )
        return StreamingResponse(
            iter([csv_buffer.getvalue()]),
            media_type=metadata.media_type,
            headers=metadata.content_disposition(),
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de exportación no soportado"
    )


@router.get(
    "/metrics",
    response_model=schemas.InventoryMetricsResponse,
)
def inventory_metrics(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    metrics = crud.compute_inventory_metrics(
        db, low_stock_threshold=settings.inventory_low_stock_threshold
    )

    totals = schemas.InventoryTotals(
        stores=len(metrics["store_metrics"]),
        devices=metrics["total_devices"],
        total_units=metrics["total_units"],
        total_value=Decimal(metrics["total_value"]),
    )

    top_stores = [
        schemas.StoreValueMetric(
            store_id=store["store_id"],
            store_name=store["store_name"],
            device_count=store["device_count"],
            total_units=store["total_units"],
            total_value=Decimal(store["total_value"]),
        )
        for store in metrics["store_metrics"]
    ]

    low_stock_devices = [
        schemas.LowStockDevice(
            store_id=device["store_id"],
            store_name=device["store_name"],
            device_id=device["device_id"],
            sku=device["sku"],
            name=device["name"],
            quantity=device["quantity"],
            unit_price=Decimal(device["unit_price"]),
        )
        for device in metrics["low_stock"]
    ]

    sales_insights = schemas.DashboardSalesInsights(
        average_ticket=0.0,
        top_products=[],
        top_customers=[],
        payment_mix=[],
    )

    audit_alerts = schemas.DashboardAuditAlerts(
        total=0,
        critical=0,
        warning=0,
        info=0,
        pending_count=0,
        acknowledged_count=0,
        highlights=[],
        acknowledged_entities=[],
    )

    global_performance = schemas.DashboardGlobalMetrics(
        total_sales=float(metrics["total_value"]),
        sales_count=metrics["sales_count"],
        total_stock=metrics["total_units"],
        open_repairs=metrics["repairs_count"],
        gross_profit=0.0,
    )

    accounts_receivable = schemas.DashboardReceivableMetrics(
        total_outstanding_debt=0.0,
        customers_with_debt=0,
        moroso_flagged=0,
        top_debtors=[],
    )

    return schemas.InventoryMetricsResponse(
        totals=totals,
        top_stores=top_stores,
        low_stock_devices=low_stock_devices,
        global_performance=global_performance,
        sales_insights=sales_insights,
        accounts_receivable=accounts_receivable,
        sales_trend=[],
        stock_breakdown=[],
        repair_mix=[],
        profit_breakdown=[],
        audit_alerts=audit_alerts,
    )
