"""Compatibilidad temporal para el reporte analítico de compras perdido al dividir reports.py."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app import crud, schemas
from backend.app.core.roles import ADMIN
from backend.app.database import get_db
from backend.app.security import require_roles
from .common import ensure_analytics_enabled

router = APIRouter(tags=["reportes"])


@router.get("/purchases", response_model=schemas.PurchaseAnalyticsResponse)
def purchases_report(
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
    data = crud.calculate_purchase_supplier_metrics(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=limit,
        offset=offset,
    )
    return schemas.PurchaseAnalyticsResponse(
        items=[schemas.PurchaseSupplierMetric(**item) for item in data]
    )


__all__ = ["router"]
