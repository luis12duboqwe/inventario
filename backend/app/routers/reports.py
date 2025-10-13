"""Reportes consolidados y bitácoras."""
from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..config import settings
from ..core.roles import AUDITORIA_ROLES, REPORTE_ROLES
from ..database import get_db
from ..security import require_roles
from ..services import analytics as analytics_service
from ..services import backups as backup_services

router = APIRouter(prefix="/reports", tags=["reportes"])


def _ensure_analytics_enabled() -> None:
    if not settings.enable_analytics_adv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionalidad no disponible")


@router.get("/audit", response_model=list[schemas.AuditLogResponse])
def audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*AUDITORIA_ROLES)),
):
    return crud.list_audit_logs(db, limit=limit)


@router.get("/analytics/rotation", response_model=schemas.AnalyticsRotationResponse)
def analytics_rotation(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    _ensure_analytics_enabled()
    data = crud.calculate_rotation_analytics(db)
    return schemas.AnalyticsRotationResponse(items=[schemas.RotationMetric(**item) for item in data])


@router.get("/analytics/aging", response_model=schemas.AnalyticsAgingResponse)
def analytics_aging(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    _ensure_analytics_enabled()
    data = crud.calculate_aging_analytics(db)
    return schemas.AnalyticsAgingResponse(items=[schemas.AgingMetric(**item) for item in data])


@router.get("/analytics/stockout_forecast", response_model=schemas.AnalyticsForecastResponse)
def analytics_forecast(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    _ensure_analytics_enabled()
    data = crud.calculate_stockout_forecast(db)
    return schemas.AnalyticsForecastResponse(items=[schemas.StockoutForecastMetric(**item) for item in data])


@router.get("/analytics/pdf")
def analytics_pdf(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    _ensure_analytics_enabled()
    rotation = crud.calculate_rotation_analytics(db)
    aging = crud.calculate_aging_analytics(db)
    forecast = crud.calculate_stockout_forecast(db)
    pdf_bytes = analytics_service.render_analytics_pdf(rotation=rotation, aging=aging, forecast=forecast)
    buffer = BytesIO(pdf_bytes)
    headers = {"Content-Disposition": "attachment; filename=softmobile_analytics.pdf"}
    return StreamingResponse(buffer, media_type="application/pdf", headers=headers)


@router.get("/inventory/pdf")
def inventory_pdf(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    snapshot = backup_services.build_inventory_snapshot(db)
    pdf_bytes = backup_services.render_snapshot_pdf(snapshot)
    buffer = BytesIO(pdf_bytes)
    headers = {
        "Content-Disposition": "attachment; filename=softmobile_inventario.pdf",
    }
    return StreamingResponse(buffer, media_type="application/pdf", headers=headers)


@router.get("/metrics", response_model=schemas.InventoryMetricsResponse)
def inventory_metrics(
    low_stock_threshold: int = Query(default=5, ge=0, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    return crud.compute_inventory_metrics(db, low_stock_threshold=low_stock_threshold)
