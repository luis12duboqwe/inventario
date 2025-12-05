from __future__ import annotations
from datetime import date, datetime
from io import BytesIO

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app import crud, schemas
from backend.app.core.roles import ADMIN, REPORTE_ROLES
from backend.app.database import get_db
from backend.app.routers.dependencies import require_reason
from backend.app.security import require_roles
from backend.app.services import analytics as analytics_service
from backend.app.services import risk_monitor
from .common import ensure_analytics_enabled, coerce_datetime

router = APIRouter(tags=["reportes"])


@router.get("/analytics/rotation", response_model=schemas.AnalyticsRotationResponse)
def analytics_rotation(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    supplier: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    ensure_analytics_enabled()
    data = crud.calculate_rotation_analytics(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=limit,
        offset=offset,
    )
    return schemas.AnalyticsRotationResponse(items=[schemas.RotationMetric(**item) for item in data])


@router.get("/analytics/aging", response_model=schemas.AnalyticsAgingResponse)
def analytics_aging(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    supplier: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    ensure_analytics_enabled()
    data = crud.calculate_aging_analytics(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=limit,
        offset=offset,
    )
    return schemas.AnalyticsAgingResponse(items=[schemas.AgingMetric(**item) for item in data])


@router.get("/analytics/stockout_forecast", response_model=schemas.AnalyticsForecastResponse)
def analytics_forecast(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    supplier: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    ensure_analytics_enabled()
    data = crud.calculate_stockout_forecast(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=limit,
        offset=offset,
    )
    return schemas.AnalyticsForecastResponse(items=[schemas.StockoutForecastMetric(**item) for item in data])


@router.get("/analytics/comparative", response_model=schemas.AnalyticsComparativeResponse)
def analytics_comparative(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    supplier: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    ensure_analytics_enabled()
    data = crud.calculate_store_comparatives(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=limit,
        offset=offset,
    )
    return schemas.AnalyticsComparativeResponse(
        items=[schemas.StoreComparativeMetric(**item) for item in data]
    )


@router.get("/analytics/profit_margin", response_model=schemas.AnalyticsProfitMarginResponse)
def analytics_profit_margin(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    supplier: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    ensure_analytics_enabled()
    data = crud.calculate_profit_margin(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=limit,
        offset=offset,
    )
    return schemas.AnalyticsProfitMarginResponse(
        items=[schemas.ProfitMarginMetric(**item) for item in data]
    )


@router.get("/analytics/sales_forecast", response_model=schemas.AnalyticsSalesProjectionResponse)
def analytics_sales_projection(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    supplier: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    ensure_analytics_enabled()
    data = crud.calculate_sales_projection(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=limit,
        offset=offset,
    )
    return schemas.AnalyticsSalesProjectionResponse(
        items=[schemas.SalesProjectionMetric(**item) for item in data]
    )


@router.get("/analytics/categories", response_model=schemas.AnalyticsCategoriesResponse)
def analytics_categories(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    ensure_analytics_enabled()
    categories = crud.list_analytics_categories(db, limit=limit, offset=offset)
    return schemas.AnalyticsCategoriesResponse(categories=categories)


@router.get("/analytics/alerts", response_model=schemas.AnalyticsAlertsResponse)
def analytics_alerts(
    store_ids: list[int] | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    supplier: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    ensure_analytics_enabled()
    data = crud.generate_analytics_alerts(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=limit,
        offset=offset,
    )
    return schemas.AnalyticsAlertsResponse(
        items=[schemas.AnalyticsAlert(**item) for item in data]
    )


@router.get("/analytics/risk", response_model=schemas.RiskAlertsResponse)
def analytics_risk(
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    discount_threshold: float = Query(default=25.0, ge=0, le=100),
    cancellation_threshold: int = Query(default=1, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    ensure_analytics_enabled()
    normalized_from = coerce_datetime(date_from)
    normalized_to = coerce_datetime(date_to)
    risk_response = risk_monitor.compute_risk_alerts(
        db,
        date_from=normalized_from,
        date_to=normalized_to,
        discount_threshold=discount_threshold,
        cancellation_threshold=cancellation_threshold,
    )
    risk_monitor.dispatch_risk_notifications(risk_response.alerts)
    return risk_response


@router.get("/analytics/realtime", response_model=schemas.AnalyticsRealtimeResponse)
def analytics_realtime(
    store_ids: list[int] | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    supplier: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    ensure_analytics_enabled()
    data = crud.calculate_realtime_store_widget(
        db,
        store_ids=store_ids,
        category=category,
        supplier=supplier,
        limit=limit,
        offset=offset,
    )
    return schemas.AnalyticsRealtimeResponse(
        items=[schemas.StoreRealtimeWidget(**item) for item in data]
    )


@router.get(
    "/analytics/store_sales_forecast",
    response_model=schemas.StoreSalesForecastResponse,
)
def analytics_store_sales_forecast(
    store_ids: list[int] | None = Query(default=None),
    horizon_days: int = Query(default=14, ge=1, le=60),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    supplier: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    ensure_analytics_enabled()
    items = crud.calculate_store_sales_forecast(
        db,
        store_ids=store_ids,
        horizon_days=horizon_days,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=limit,
        offset=offset,
    )
    return schemas.StoreSalesForecastResponse(
        items=[schemas.StoreSalesForecast(**item) for item in items]
    )


@router.get(
    "/analytics/reorder_suggestions",
    response_model=schemas.ReorderSuggestionsResponse,
)
def analytics_reorder_suggestions(
    store_ids: list[int] | None = Query(default=None),
    horizon_days: int = Query(default=7, ge=1, le=60),
    safety_days: int = Query(default=2, ge=0, le=14),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=120),
    supplier: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    ensure_analytics_enabled()
    items = crud.calculate_reorder_suggestions(
        db,
        store_ids=store_ids,
        horizon_days=horizon_days,
        safety_days=safety_days,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=limit,
        offset=offset,
    )
    return schemas.ReorderSuggestionsResponse(
        items=[schemas.ReorderSuggestion(**item) for item in items]
    )


@router.get(
    "/analytics/return_anomalies",
    response_model=schemas.ReturnAnomaliesResponse,
)
def analytics_return_anomalies(
    store_ids: list[int] | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    sigma_threshold: float = Query(default=2.0, ge=0.5, le=4.0),
    min_returns: int = Query(default=3, ge=1, le=50),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    ensure_analytics_enabled()
    items = crud.detect_return_anomalies(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        sigma_threshold=sigma_threshold,
        min_returns=min_returns,
        limit=limit,
        offset=offset,
    )
    return schemas.ReturnAnomaliesResponse(
        items=[schemas.ReturnAnomaly(**item) for item in items]
    )


@router.get("/analytics/pdf", response_model=schemas.BinaryFileResponse)
def analytics_pdf(
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
    export_limit = 200
    rotation = crud.calculate_rotation_analytics(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=export_limit,
        offset=0,
    )
    aging = crud.calculate_aging_analytics(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=export_limit,
        offset=0,
    )
    forecast = crud.calculate_stockout_forecast(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=export_limit,
        offset=0,
    )
    comparatives = crud.calculate_store_comparatives(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=export_limit,
        offset=0,
    )
    profit = crud.calculate_profit_margin(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=export_limit,
        offset=0,
    )
    projection = crud.calculate_sales_projection(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
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
