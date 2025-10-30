"""Reportes consolidados y bitácoras."""
from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from io import BytesIO, StringIO
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..config import settings
from ..core.roles import ADMIN
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services import analytics as analytics_service
from ..services import audit as audit_service
from ..services import backups as backup_services
from ..services import global_reports as global_reports_service
from ..services import customer_reports
from ..services import inventory_reports as inventory_reports_service
from ..utils import audit as audit_utils
from backend.schemas.common import Page, PageParams

router = APIRouter(prefix="/reports", tags=["reportes"])


def _ensure_analytics_enabled() -> None:
    if not settings.enable_analytics_adv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionalidad no disponible")


def _coerce_datetime(value: datetime | date | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, datetime.min.time())


# // [PACK29-*] Normalización de rangos para reportes de ventas
def _normalize_sales_range(
    date_from: datetime | date | None,
    date_to: datetime | date | None,
) -> tuple[datetime | None, datetime | None]:
    normalized_from = _coerce_datetime(date_from)
    normalized_to = _coerce_datetime(date_to)
    if isinstance(date_to, date) and not isinstance(date_to, datetime):
        normalized_to = normalized_to + timedelta(days=1) if normalized_to else None
    elif isinstance(date_to, datetime) and normalized_to is not None:
        normalized_to = normalized_to + timedelta(microseconds=1)
    return normalized_from, normalized_to


# // [PACK29-*] Normaliza fechas para construir nombres de archivo
def _format_range_value(value: datetime | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    return value.isoformat()


@router.get(
    "/global/overview",
    response_model=schemas.GlobalReportOverview,
    dependencies=[Depends(require_roles(ADMIN))],
)
def global_report_overview(
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    module: str | None = Query(default=None, max_length=80),
    severity: schemas.SystemLogLevel | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    normalized_from = _coerce_datetime(date_from)
    normalized_to = _coerce_datetime(date_to)
    return crud.build_global_report_overview(
        db,
        date_from=normalized_from,
        date_to=normalized_to,
        module=module,
        severity=severity,
    )


@router.get(
    "/global/dashboard",
    response_model=schemas.GlobalReportDashboard,
    dependencies=[Depends(require_roles(ADMIN))],
)
def global_report_dashboard(
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    module: str | None = Query(default=None, max_length=80),
    severity: schemas.SystemLogLevel | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    normalized_from = _coerce_datetime(date_from)
    normalized_to = _coerce_datetime(date_to)
    return crud.build_global_report_dashboard(
        db,
        date_from=normalized_from,
        date_to=normalized_to,
        module=module,
        severity=severity,
    )


@router.get(
    "/global/export",
    response_model=schemas.BinaryFileResponse,
    dependencies=[Depends(require_roles(ADMIN))],
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
    normalized_from = _coerce_datetime(date_from)
    normalized_to = _coerce_datetime(date_to)
    overview = crud.build_global_report_overview(
        db,
        date_from=normalized_from,
        date_to=normalized_to,
        module=module,
        severity=severity,
    )
    dashboard = crud.build_global_report_dashboard(
        db,
        date_from=normalized_from,
        date_to=normalized_to,
        module=module,
        severity=severity,
    )

    if format == "pdf":
        pdf_bytes = global_reports_service.render_global_report_pdf(overview, dashboard)
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
        workbook = global_reports_service.render_global_report_xlsx(overview, dashboard)
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
        csv_buffer = global_reports_service.render_global_report_csv(overview, dashboard)
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



# // [PACK29-*] Reporte resumen de ventas con filtros de fecha y sucursal
@router.get(
    "/sales/summary",
    response_model=schemas.SalesSummaryReport,
    dependencies=[Depends(require_roles(ADMIN))],
)
def get_sales_summary_report(
    date_from: datetime | date | None = Query(default=None, alias="from"),
    date_to: datetime | date | None = Query(default=None, alias="to"),
    branch_id: int | None = Query(default=None, alias="branchId", ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    _ensure_analytics_enabled()
    normalized_from, normalized_to = _normalize_sales_range(date_from, date_to)
    if normalized_from and normalized_to and normalized_from >= normalized_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El rango de fechas es inválido.",
        )
    return crud.build_sales_summary_report(
        db,
        date_from=normalized_from,
        date_to=normalized_to,
        store_id=branch_id,
    )


# // [PACK29-*] Reporte de top de productos vendidos
@router.get(
    "/sales/by-product",
    response_model=list[schemas.SalesByProductItem],
    dependencies=[Depends(require_roles(ADMIN))],
)
def get_sales_by_product_report(
    date_from: datetime | date | None = Query(default=None, alias="from"),
    date_to: datetime | date | None = Query(default=None, alias="to"),
    branch_id: int | None = Query(default=None, alias="branchId", ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    format: Literal["json", "csv"] = Query(default="json"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    _ensure_analytics_enabled()
    normalized_from, normalized_to = _normalize_sales_range(date_from, date_to)
    if normalized_from and normalized_to and normalized_from >= normalized_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El rango de fechas es inválido.",
        )
    items = crud.build_sales_by_product_report(
        db,
        date_from=normalized_from,
        date_to=normalized_to,
        store_id=branch_id,
        limit=limit,
    )
    if format == "csv":
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["SKU", "Producto", "Cantidad", "Ventas brutas", "Ventas netas"])
        for item in items:
            writer.writerow([
                item.sku,
                item.name,
                item.quantity,
                f"{item.gross:.2f}",
                f"{item.net:.2f}",
            ])
        filename_parts: list[str] = []
        from_label = _format_range_value(date_from)
        to_label = _format_range_value(date_to)
        if from_label:
            filename_parts.append(from_label)
        if to_label:
            filename_parts.append(to_label)
        if branch_id is not None:
            filename_parts.append(f"sucursal-{branch_id}")
        suffix = "_al_".join(filename_parts)
        filename = "top-productos.csv" if not suffix else f"top-productos_{suffix}.csv"
        metadata = schemas.BinaryFileResponse(
            filename=filename,
            media_type="text/csv;charset=utf-8",
        )
        buffer.seek(0)
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type=metadata.media_type,
            headers=metadata.content_disposition(),
        )
    return items


# // [PACK29-*] Sugerencia de cierre de caja considerando ventas y devoluciones
@router.get(
    "/cash-close",
    response_model=schemas.CashCloseReport,
    dependencies=[Depends(require_roles(ADMIN))],
)
def get_cash_close_report(
    target_date: date | None = Query(default=None, alias="date"),
    branch_id: int | None = Query(default=None, alias="branchId", ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    _ensure_analytics_enabled()
    report_date = target_date or datetime.utcnow().date()
    start_of_day = datetime.combine(report_date, datetime.min.time())
    end_of_day = start_of_day + timedelta(days=1)
    return crud.build_cash_close_report(
        db,
        date_from=start_of_day,
        date_to=end_of_day,
        store_id=branch_id,
    )


@router.get("/customers/portfolio", response_model=schemas.CustomerPortfolioReport, dependencies=[Depends(require_roles(ADMIN))])
def customer_portfolio_report(
    request: Request,
    category: Literal["delinquent", "frequent"] = Query(default="delinquent"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    export: Literal["json", "pdf", "xlsx"] = Query(default="json"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    x_reason: str | None = Header(default=None, alias="X-Reason"),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El rango de fechas es inválido.",
        )

    report = crud.build_customer_portfolio(
        db,
        category=category,
        limit=limit,
        offset=offset,
        date_from=date_from,
        date_to=date_to,
    )

    if export == "json":
        return report

    require_reason(request, x_reason)

    if export == "pdf":
        pdf_bytes = customer_reports.render_customer_portfolio_pdf(report)
        buffer = BytesIO(pdf_bytes)
        headers = {
            "Content-Disposition": f"attachment; filename=clientes_{category}.pdf"
        }
        return StreamingResponse(buffer, media_type="application/pdf", headers=headers)
    if export == "xlsx":
        workbook = customer_reports.render_customer_portfolio_xlsx(report)
        headers = {
            "Content-Disposition": f"attachment; filename=clientes_{category}.xlsx"
        }
        return StreamingResponse(
            workbook,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers,
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de exportación no soportado"
    )


@router.get("/audit", response_model=Page[schemas.AuditLogResponse], dependencies=[Depends(require_roles(ADMIN))])
def audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action: str | None = Query(default=None, max_length=120),
    entity_type: str | None = Query(default=None, max_length=80),
    performed_by_id: int | None = Query(default=None, ge=1),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    pagination: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
) -> Page[schemas.AuditLogResponse]:
    page_offset = pagination.offset if (pagination.page > 1 and offset == 0) else offset
    page_size = min(pagination.size, limit)
    total = crud.count_audit_logs(
        db,
        action=action,
        entity_type=entity_type,
        performed_by_id=performed_by_id,
        date_from=date_from,
        date_to=date_to,
    )
    logs = crud.list_audit_logs(
        db,
        limit=page_size,
        offset=page_offset,
        action=action,
        entity_type=entity_type,
        performed_by_id=performed_by_id,
        date_from=date_from,
        date_to=date_to,
    )
    page_number = (
        pagination.page if offset == 0 else max(1, (page_offset // page_size) + 1)
    )
    return Page.from_items(logs, page=page_number, size=page_size, total=total)


@router.get("/audit/pdf", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(ADMIN))])
def audit_logs_pdf(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action: str | None = Query(default=None, max_length=120),
    entity_type: str | None = Query(default=None, max_length=80),
    performed_by_id: int | None = Query(default=None, ge=1),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    logs = crud.list_audit_logs(
        db,
        limit=limit,
        offset=offset,
        action=action,
        entity_type=entity_type,
        performed_by_id=performed_by_id,
        date_from=date_from,
        date_to=date_to,
    )
    summary = audit_utils.summarize_alerts(logs)
    filters: dict[str, str] = {}
    if action:
        filters["Acción"] = action
    if entity_type:
        filters["Tipo de entidad"] = entity_type
    if performed_by_id is not None:
        filters["Usuario"] = str(performed_by_id)
    if date_from:
        filters["Desde"] = str(date_from)
    if date_to:
        filters["Hasta"] = str(date_to)
    pdf_bytes = audit_service.render_audit_pdf(logs, filters=filters, alerts=summary)
    buffer = BytesIO(pdf_bytes)
    metadata = schemas.BinaryFileResponse(
        filename="auditoria_softmobile.pdf",
        media_type="application/pdf",
    )
    return StreamingResponse(
        buffer,
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/analytics/rotation", response_model=schemas.AnalyticsRotationResponse, dependencies=[Depends(require_roles(ADMIN))])
def analytics_rotation(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    _ensure_analytics_enabled()
    data = crud.calculate_rotation_analytics(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        limit=limit,
        offset=offset,
    )
    return schemas.AnalyticsRotationResponse(items=[schemas.RotationMetric(**item) for item in data])


@router.get("/analytics/aging", response_model=schemas.AnalyticsAgingResponse, dependencies=[Depends(require_roles(ADMIN))])
def analytics_aging(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    _ensure_analytics_enabled()
    data = crud.calculate_aging_analytics(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        limit=limit,
        offset=offset,
    )
    return schemas.AnalyticsAgingResponse(items=[schemas.AgingMetric(**item) for item in data])


@router.get("/analytics/stockout_forecast", response_model=schemas.AnalyticsForecastResponse, dependencies=[Depends(require_roles(ADMIN))])
def analytics_forecast(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    _ensure_analytics_enabled()
    data = crud.calculate_stockout_forecast(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        limit=limit,
        offset=offset,
    )
    return schemas.AnalyticsForecastResponse(items=[schemas.StockoutForecastMetric(**item) for item in data])


@router.get("/analytics/comparative", response_model=schemas.AnalyticsComparativeResponse, dependencies=[Depends(require_roles(ADMIN))])
def analytics_comparative(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    _ensure_analytics_enabled()
    data = crud.calculate_store_comparatives(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        limit=limit,
        offset=offset,
    )
    return schemas.AnalyticsComparativeResponse(
        items=[schemas.StoreComparativeMetric(**item) for item in data]
    )


@router.get("/analytics/profit_margin", response_model=schemas.AnalyticsProfitMarginResponse, dependencies=[Depends(require_roles(ADMIN))])
def analytics_profit_margin(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    _ensure_analytics_enabled()
    data = crud.calculate_profit_margin(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        limit=limit,
        offset=offset,
    )
    return schemas.AnalyticsProfitMarginResponse(
        items=[schemas.ProfitMarginMetric(**item) for item in data]
    )


@router.get("/analytics/sales_forecast", response_model=schemas.AnalyticsSalesProjectionResponse, dependencies=[Depends(require_roles(ADMIN))])
def analytics_sales_projection(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    _ensure_analytics_enabled()
    data = crud.calculate_sales_projection(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        limit=limit,
        offset=offset,
    )
    return schemas.AnalyticsSalesProjectionResponse(
        items=[schemas.SalesProjectionMetric(**item) for item in data]
    )


@router.get("/analytics/categories", response_model=schemas.AnalyticsCategoriesResponse, dependencies=[Depends(require_roles(ADMIN))])
def analytics_categories(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    _ensure_analytics_enabled()
    categories = crud.list_analytics_categories(db, limit=limit, offset=offset)
    return schemas.AnalyticsCategoriesResponse(categories=categories)


@router.get("/analytics/alerts", response_model=schemas.AnalyticsAlertsResponse, dependencies=[Depends(require_roles(ADMIN))])
def analytics_alerts(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    _ensure_analytics_enabled()
    data = crud.generate_analytics_alerts(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        limit=limit,
        offset=offset,
    )
    return schemas.AnalyticsAlertsResponse(
        items=[schemas.AnalyticsAlert(**item) for item in data]
    )


@router.get("/analytics/realtime", response_model=schemas.AnalyticsRealtimeResponse, dependencies=[Depends(require_roles(ADMIN))])
def analytics_realtime(
    store_ids: list[int] | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    _ensure_analytics_enabled()
    data = crud.calculate_realtime_store_widget(
        db,
        store_ids=store_ids,
        category=category,
        limit=limit,
        offset=offset,
    )
    return schemas.AnalyticsRealtimeResponse(
        items=[schemas.StoreRealtimeWidget(**item) for item in data]
    )


@router.get("/analytics/pdf", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(ADMIN))])
def analytics_pdf(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    _ensure_analytics_enabled()
    export_limit = 200
    rotation = crud.calculate_rotation_analytics(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        limit=export_limit,
        offset=0,
    )
    aging = crud.calculate_aging_analytics(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        limit=export_limit,
        offset=0,
    )
    forecast = crud.calculate_stockout_forecast(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        limit=export_limit,
        offset=0,
    )
    comparatives = crud.calculate_store_comparatives(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        limit=export_limit,
        offset=0,
    )
    profit = crud.calculate_profit_margin(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        limit=export_limit,
        offset=0,
    )
    projection = crud.calculate_sales_projection(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        limit=export_limit,
        offset=0,
    )
    pdf_bytes = analytics_service.render_analytics_pdf(
        rotation=rotation,
        aging=aging,
        forecast=forecast,
        comparatives=comparatives,
        profit=profit,
        projection=projection,
    )
    buffer = BytesIO(pdf_bytes)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_analytics.pdf",
        media_type="application/pdf",
    )
    return StreamingResponse(
        buffer,
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/analytics/export.csv", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(ADMIN))])
def analytics_export_csv(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    _ensure_analytics_enabled()
    comparatives = crud.calculate_store_comparatives(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    profit = crud.calculate_profit_margin(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    projection = crud.calculate_sales_projection(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Comparativo sucursales"])
    writer.writerow([
        "Sucursal",
        "Dispositivos",
        "Unidades",
        "Valor inventario",
        "Rotación promedio",
        "Envejecimiento promedio",
        "Ventas 30d",
        "Órdenes 30d",
    ])
    for item in comparatives:
        writer.writerow(
            [
                item["store_name"],
                item["device_count"],
                item["total_units"],
                f"{item['inventory_value']:.2f}",
                f"{item['average_rotation']:.2f}",
                f"{item['average_aging_days']:.2f}",
                f"{item['sales_last_30_days']:.2f}",
                item["sales_count_last_30_days"],
            ]
        )

    writer.writerow([])
    writer.writerow(["Margen por sucursal"])
    writer.writerow(["Sucursal", "Ingresos", "Costo", "Utilidad", "% Margen"])
    for item in profit:
        writer.writerow(
            [
                item["store_name"],
                f"{item['revenue']:.2f}",
                f"{item['cost']:.2f}",
                f"{item['profit']:.2f}",
                f"{item['margin_percent']:.2f}",
            ]
        )

    writer.writerow([])
    writer.writerow(["Proyección ventas 30 días"])
    writer.writerow([
        "Sucursal",
        "Unidades diarias",
        "Ticket promedio",
        "Unidades proyectadas",
        "Ingresos proyectados",
        "Confianza",
    ])
    for item in projection:
        writer.writerow(
            [
                item["store_name"],
                f"{item['average_daily_units']:.2f}",
                f"{item['average_ticket']:.2f}",
                f"{item['projected_units']:.2f}",
                f"{item['projected_revenue']:.2f}",
                f"{item['confidence']:.2f}",
            ]
        )

    buffer.seek(0)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_analytics.csv",
        media_type="text/csv",
    )
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/inventory/current", response_model=schemas.InventoryCurrentReport, dependencies=[Depends(require_roles(ADMIN))])
def inventory_current(
    store_ids: list[int] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    return crud.get_inventory_current_report(db, store_ids=store_ids)


@router.get("/inventory/current/csv", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(ADMIN))])
def inventory_current_csv(
    store_ids: list[int] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    report = crud.get_inventory_current_report(db, store_ids=store_ids)

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Existencias actuales"])
    writer.writerow(["Sucursales consideradas", report.totals.stores])
    writer.writerow(["Dispositivos catalogados", report.totals.devices])
    writer.writerow(["Unidades totales", report.totals.total_units])
    writer.writerow(["Valor consolidado (MXN)", f"{report.totals.total_value:.2f}"])
    writer.writerow([])
    writer.writerow(["Sucursal", "Dispositivos", "Unidades", "Valor total (MXN)"])
    for store in report.stores:
        writer.writerow(
            [
                store.store_name,
                store.device_count,
                store.total_units,
                f"{store.total_value:.2f}",
            ]
        )

    buffer.seek(0)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_existencias.csv",
        media_type="text/csv",
    )
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/inventory/current/pdf", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(ADMIN))])
def inventory_current_pdf(
    store_ids: list[int] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    report = crud.get_inventory_current_report(db, store_ids=store_ids)
    pdf_bytes = inventory_reports_service.render_inventory_current_pdf(report)
    buffer = BytesIO(pdf_bytes)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_existencias.pdf",
        media_type="application/pdf",
    )
    return StreamingResponse(
        buffer,
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/inventory/current/xlsx", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(ADMIN))])
def inventory_current_excel(
    store_ids: list[int] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    report = crud.get_inventory_current_report(db, store_ids=store_ids)
    workbook_buffer = inventory_reports_service.build_inventory_current_excel(report)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_existencias.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    return StreamingResponse(
        iter([workbook_buffer.getvalue()]),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/inventory/value", response_model=schemas.InventoryValueReport, dependencies=[Depends(require_roles(ADMIN))])
def inventory_value(
    store_ids: list[int] | None = Query(default=None),
    categories: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    normalized_categories = [category for category in categories or [] if category]
    return crud.get_inventory_value_report(
        db,
        store_ids=store_ids,
        categories=normalized_categories if normalized_categories else None,
    )


@router.get(
    "/inventory/movements",
    response_model=schemas.InventoryMovementsReport,
    dependencies=[Depends(require_roles(ADMIN))],
)
def inventory_movements(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    movement_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    movement_enum: models.MovementType | None = None
    if movement_type:
        try:
            movement_enum = models.MovementType(movement_type)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tipo de movimiento inválido",
            ) from exc
    return crud.get_inventory_movements_report(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        movement_type=movement_enum,
    )


@router.get(
    "/inventory/top-products",
    response_model=schemas.TopProductsReport,
    dependencies=[Depends(require_roles(ADMIN))],
)
def inventory_top_products(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    return crud.get_top_selling_products(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.get("/inventory/pdf", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(ADMIN))])
def inventory_pdf(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    snapshot = backup_services.build_inventory_snapshot(db)
    pdf_bytes = backup_services.render_snapshot_pdf(snapshot)
    buffer = BytesIO(pdf_bytes)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_inventario.pdf",
        media_type="application/pdf",
    )
    return StreamingResponse(
        buffer,
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/inventory/csv", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(ADMIN))])
def inventory_csv(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    snapshot = backup_services.build_inventory_snapshot(db)
    buffer = StringIO()
    writer = csv.writer(buffer)

    writer.writerow(["Inventario corporativo"])
    writer.writerow(["Generado", datetime.utcnow().isoformat()])

    consolidated_total = 0.0

    for store in snapshot.get("stores", []):
        writer.writerow([])
        writer.writerow([f"Sucursal: {store['name']}", store.get("location", "-"), store.get("timezone", "UTC")])
        writer.writerow(
            [
                "SKU",
                "Nombre",
                "Cantidad",
                "Precio unitario",
                "Valor total",
                "IMEI",
                "Serie",
                "Marca",
                "Modelo",
                "Proveedor",
                "Color",
                "Capacidad (GB)",
                "Estado",
                "Lote",
                "Fecha compra",
                "Garantía (meses)",
                "Costo unitario",
                "Margen (%)",
            ]
        )
        store_total = 0.0
        for device in store.get("devices", []):
            inventory_value_raw = device.get("inventory_value", 0)
            unit_price_raw = device.get("unit_price", 0)
            costo_unitario_raw = device.get("costo_unitario", 0.0)
            margen_raw = device.get("margen_porcentaje", 0.0)

            try:
                inventory_value_float = float(inventory_value_raw)
            except (TypeError, ValueError):
                inventory_value_float = 0.0

            try:
                unit_price_float = float(unit_price_raw)
            except (TypeError, ValueError):
                unit_price_float = 0.0

            try:
                costo_unitario = float(costo_unitario_raw)
            except (TypeError, ValueError):
                costo_unitario = 0.0

            try:
                margen_porcentaje = float(margen_raw)
            except (TypeError, ValueError):
                margen_porcentaje = 0.0

            store_total += inventory_value_float
            garantia = device.get("garantia_meses")
            writer.writerow(
                [
                    device.get("sku"),
                    device.get("name"),
                    device.get("quantity"),
                    f"{unit_price_float:.2f}",
                    f"{inventory_value_float:.2f}",
                    device.get("imei") or "-",
                    device.get("serial") or "-",
                    device.get("marca") or "-",
                    device.get("modelo") or "-",
                    device.get("proveedor") or "-",
                    device.get("color") or "-",
                    device.get("capacidad_gb") if device.get("capacidad_gb") is not None else "-",
                    device.get("estado_comercial", "-"),
                    device.get("lote") or "-",
                    device.get("fecha_compra") or "-",
                    garantia if garantia is not None else "-",
                    f"{costo_unitario:.2f}",
                    f"{margen_porcentaje:.2f}",
                ]
            )

        registered_value_raw = store.get("inventory_value")
        try:
            registered_value = float(registered_value_raw) if registered_value_raw is not None else store_total
        except (TypeError, ValueError):
            registered_value = store_total

        totals_padding = [""] * 13
        writer.writerow(["TOTAL SUCURSAL", "", "", "", f"{store_total:.2f}", *totals_padding])
        writer.writerow(["VALOR CONTABLE", "", "", "", f"{registered_value:.2f}", *totals_padding])

        consolidated_total += store_total

    summary = snapshot.get("summary") or {}
    if summary:
        writer.writerow([])
        writer.writerow(["Resumen corporativo"])
        writer.writerow(["Sucursales auditadas", summary.get("store_count", 0)])
        writer.writerow(["Dispositivos catalogados", summary.get("device_records", 0)])
        writer.writerow(["Unidades totales", summary.get("total_units", 0)])
        summary_value_raw = summary.get("inventory_value")
        try:
            summary_value = float(summary_value_raw) if summary_value_raw is not None else 0.0
        except (TypeError, ValueError):
            summary_value = 0.0
        writer.writerow(["Inventario consolidado registrado (MXN)", f"{summary_value:.2f}"])
        writer.writerow(["Inventario consolidado calculado (MXN)", f"{consolidated_total:.2f}"])

    buffer.seek(0)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_inventario.csv",
        media_type="text/csv",
    )
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/inventory/value/csv", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(ADMIN))])
def inventory_value_csv(
    store_ids: list[int] | None = Query(default=None),
    categories: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    normalized_categories = [category for category in categories or [] if category]
    report = crud.get_inventory_value_report(
        db,
        store_ids=store_ids,
        categories=normalized_categories if normalized_categories else None,
    )

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Valoración de inventario"])
    writer.writerow(["Sucursales consideradas", len(report.stores)])
    writer.writerow([])
    writer.writerow(["Sucursal", "Valor total (MXN)", "Valor costo (MXN)", "Margen estimado (MXN)"])
    for store in report.stores:
        writer.writerow(
            [
                store.store_name,
                f"{store.valor_total:.2f}",
                f"{store.valor_costo:.2f}",
                f"{store.margen_total:.2f}",
            ]
        )

    writer.writerow([])
    writer.writerow([
        "Totales corporativos",
        f"{report.totals.valor_total:.2f}",
        f"{report.totals.valor_costo:.2f}",
        f"{report.totals.margen_total:.2f}",
    ])

    buffer.seek(0)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_valor_inventario.csv",
        media_type="text/csv",
    )
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/inventory/value/pdf", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(ADMIN))])
def inventory_value_pdf(
    store_ids: list[int] | None = Query(default=None),
    categories: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    normalized_categories = [category for category in categories or [] if category]
    report = crud.get_inventory_value_report(
        db,
        store_ids=store_ids,
        categories=normalized_categories if normalized_categories else None,
    )
    pdf_bytes = inventory_reports_service.render_inventory_value_pdf(report)
    buffer = BytesIO(pdf_bytes)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_valor_inventario.pdf",
        media_type="application/pdf",
    )
    return StreamingResponse(
        buffer,
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/inventory/value/xlsx", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(ADMIN))])
def inventory_value_excel(
    store_ids: list[int] | None = Query(default=None),
    categories: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    normalized_categories = [category for category in categories or [] if category]
    report = crud.get_inventory_value_report(
        db,
        store_ids=store_ids,
        categories=normalized_categories if normalized_categories else None,
    )
    workbook_buffer = inventory_reports_service.build_inventory_value_excel(report)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_valor_inventario.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    return StreamingResponse(
        iter([workbook_buffer.getvalue()]),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/inventory/movements/csv", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(ADMIN))])
def inventory_movements_csv(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    movement_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    movement_enum: models.MovementType | None = None
    if movement_type:
        try:
            movement_enum = models.MovementType(movement_type)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tipo de movimiento inválido",
            ) from exc

    report = crud.get_inventory_movements_report(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        movement_type=movement_enum,
    )

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Movimientos de inventario"])
    writer.writerow(["Total registros", report.resumen.total_movimientos])
    writer.writerow(["Total unidades", report.resumen.total_unidades])
    writer.writerow(["Valor total (MXN)", f"{report.resumen.total_valor:.2f}"])
    writer.writerow([])
    writer.writerow(["Resumen por tipo"])
    writer.writerow(["Tipo", "Cantidad", "Valor (MXN)"])
    for entry in report.resumen.por_tipo:
        writer.writerow(
            [
                entry.tipo_movimiento.value,
                entry.total_cantidad,
                f"{entry.total_valor:.2f}",
            ]
        )

    writer.writerow([])
    writer.writerow(["Acumulado por periodo"])
    writer.writerow(["Fecha", "Tipo", "Cantidad", "Valor (MXN)"])
    for period_entry in report.periodos:
        writer.writerow(
            [
                period_entry.periodo.isoformat(),
                period_entry.tipo_movimiento.value,
                period_entry.total_cantidad,
                f"{period_entry.total_valor:.2f}",
            ]
        )

    writer.writerow([])
    writer.writerow(["Detalle de movimientos"])
    writer.writerow(
        [
            "ID",
            "Fecha",
            "Tipo",
            "Cantidad",
            "Valor (MXN)",
            "Sucursal destino",
            "Sucursal origen",
            "Usuario",
            "Referencia",
            "Comentario",
            "Última acción",
        ]
    )
    for movement in report.movimientos:
        if movement.referencia_tipo and movement.referencia_id:
            reference_value = f"{movement.referencia_tipo}:{movement.referencia_id}"
        elif movement.referencia_id:
            reference_value = movement.referencia_id
        elif movement.referencia_tipo:
            reference_value = movement.referencia_tipo
        else:
            reference_value = "-"
        last_action = "-"
        if movement.ultima_accion:
            timestamp = movement.ultima_accion.timestamp.strftime("%d/%m/%Y %H:%M")
            actor = movement.ultima_accion.usuario or "-"
            last_action = f"{movement.ultima_accion.accion} · {actor} · {timestamp}"
        writer.writerow(
            [
                movement.id,
                movement.fecha.isoformat(),
                movement.tipo_movimiento.value,
                movement.cantidad,
                f"{movement.valor_total:.2f}",
                movement.sucursal_destino or "-",
                movement.sucursal_origen or "-",
                movement.usuario or "-",
                reference_value,
                movement.comentario or "-",
                last_action,
            ]
        )

    buffer.seek(0)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_movimientos.csv",
        media_type="text/csv",
    )
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/inventory/movements/pdf", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(ADMIN))])
def inventory_movements_pdf(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    movement_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    movement_enum: models.MovementType | None = None
    if movement_type:
        try:
            movement_enum = models.MovementType(movement_type)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tipo de movimiento inválido",
            ) from exc

    report = crud.get_inventory_movements_report(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        movement_type=movement_enum,
    )
    pdf_bytes = inventory_reports_service.render_inventory_movements_pdf(report)
    buffer = BytesIO(pdf_bytes)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_movimientos.pdf",
        media_type="application/pdf",
    )
    return StreamingResponse(
        buffer,
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/inventory/movements/xlsx", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(ADMIN))])
def inventory_movements_excel(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    movement_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    movement_enum: models.MovementType | None = None
    if movement_type:
        try:
            movement_enum = models.MovementType(movement_type)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tipo de movimiento inválido",
            ) from exc

    report = crud.get_inventory_movements_report(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        movement_type=movement_enum,
    )
    workbook_buffer = inventory_reports_service.build_inventory_movements_excel(report)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_movimientos.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    return StreamingResponse(
        iter([workbook_buffer.getvalue()]),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/inventory/top-products/pdf", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(ADMIN))])
def inventory_top_products_pdf(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    report = crud.get_top_selling_products(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    pdf_bytes = inventory_reports_service.render_top_products_pdf(report)
    buffer = BytesIO(pdf_bytes)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_top_productos.pdf",
        media_type="application/pdf",
    )
    return StreamingResponse(
        buffer,
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/inventory/top-products/xlsx", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(ADMIN))])
def inventory_top_products_excel(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    report = crud.get_top_selling_products(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    workbook_buffer = inventory_reports_service.build_top_products_excel(report)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_top_productos.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    return StreamingResponse(
        iter([workbook_buffer.getvalue()]),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/inventory/top-products/csv", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(ADMIN))])
def inventory_top_products_csv(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    report = crud.get_top_selling_products(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Productos más vendidos"])
    writer.writerow(["Total unidades", report.total_unidades])
    writer.writerow(["Ingresos totales (MXN)", f"{report.total_ingresos:.2f}"])
    writer.writerow([])
    writer.writerow(
        [
            "SKU",
            "Producto",
            "Sucursal",
            "Unidades vendidas",
            "Ingresos (MXN)",
            "Margen estimado (MXN)",
        ]
    )
    for item in report.items:
        writer.writerow(
            [
                item.sku,
                item.nombre,
                item.store_name,
                item.unidades_vendidas,
                f"{item.ingresos_totales:.2f}",
                f"{item.margen_estimado:.2f}",
            ]
        )

    buffer.seek(0)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_top_productos.csv",
        media_type="text/csv",
    )
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get(
    "/inventory/supplier-batches",
    response_model=Page[schemas.SupplierBatchOverviewItem],
    dependencies=[Depends(require_roles(ADMIN))],
)
def inventory_supplier_batches(
    store_id: int = Query(..., ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pagination: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
) -> Page[schemas.SupplierBatchOverviewItem]:
    page_offset = pagination.offset if (pagination.page > 1 and offset == 0) else offset
    page_size = min(pagination.size, limit)
    total = crud.count_supplier_batch_overview(db, store_id=store_id)
    overview = crud.get_supplier_batch_overview(
        db,
        store_id=store_id,
        limit=page_size,
        offset=page_offset,
    )
    return Page.from_items(
        overview,
        page=pagination.page,
        size=page_size,
        total=total,
    )


@router.get("/metrics", response_model=schemas.InventoryMetricsResponse, dependencies=[Depends(require_roles(ADMIN))])
def inventory_metrics(
    low_stock_threshold: int = Query(default=5, ge=0, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    return crud.compute_inventory_metrics(db, low_stock_threshold=low_stock_threshold)
