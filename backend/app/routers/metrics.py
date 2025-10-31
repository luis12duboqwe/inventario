"""Endpoints de métricas globales /reports para el dashboard."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db

router = APIRouter(prefix="/reports", tags=["reportes"])

@router.get("/metrics", status_code=status.HTTP_200_OK)
def get_inventory_metrics(
    low_stock_threshold: int = Query(default=5, ge=0, le=1000),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    # Métricas globales mínimas para que el dashboard funcione
    stores = crud.list_stores(db, limit=200, offset=0)
    total_stock = 0
    top_skus: list[dict[str, Any]] = []

    for s in stores:
        devices = crud.list_devices(db, s.id, limit=1000, offset=0)
        total_stock += sum(1 for _ in devices)
        # Nota: en el futuro agregar agregaciones por SKU

    metrics = {
        "low_stock_count": 0,
        "alerts": 0,
        "top_skus": top_skus,
        "global_performance": {
            "total_sales": 0,
            "sales_count": 0,
            "total_stock": total_stock,
            "open_repairs": 0,
            "gross_profit": 0,
        },
        "sales_trend": [],
        "stock_breakdown": [{"label": s.name, "value": 0} for s in stores],
    }
    return metrics
