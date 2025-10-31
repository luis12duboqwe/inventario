"""Endpoints de analítica avanzada (rotación, envejecimiento, alertas, PDF) para Softmobile 2025 v2.2.0.
Devolvemos estructuras compatibles con el frontend actual. Si no hay datos, mandamos listas vacías.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db
from ..services.analytics import render_analytics_pdf

router = APIRouter(prefix="/reports/analytics", tags=["analitica"])

# ---- Helpers ----------------------------------------------------------------

def _parse_ids(csv: str | None) -> list[int]:
    if not csv:
        return []
    out: list[int] = []
    for part in csv.split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out

# ---- Endpoints de datos (JSON) ---------------------------------------------

@router.get("/rotation", status_code=status.HTTP_200_OK)
def get_rotation(
    db: Session = Depends(get_db),
    store_ids: str | None = Query(default=None, alias="storeIds"),
    category: str | None = Query(default=None),
) -> dict[str, Any]:
    # TODO: computar desde ventas/stock reales. Por ahora estructura vacía.
    return {"items": []}

@router.get("/aging", status_code=status.HTTP_200_OK)
def get_aging(
    db: Session = Depends(get_db),
    store_ids: str | None = Query(default=None, alias="storeIds"),
    category: str | None = Query(default=None),
) -> dict[str, Any]:
    return {"items": []}

@router.get("/stockout_forecast", status_code=status.HTTP_200_OK)
def get_stockout_forecast(
    db: Session = Depends(get_db),
    store_ids: str | None = Query(default=None, alias="storeIds"),
    category: str | None = Query(default=None),
) -> dict[str, Any]:
    return {"items": []}

@router.get("/comparative", status_code=status.HTTP_200_OK)
def get_comparative(
    db: Session = Depends(get_db),
    store_ids: str | None = Query(default=None, alias="storeIds"),
    category: str | None = Query(default=None),
) -> dict[str, Any]:
    return {"stores": []}

@router.get("/profit_margin", status_code=status.HTTP_200_OK)
def get_profit_margin(
    db: Session = Depends(get_db),
    store_ids: str | None = Query(default=None, alias="storeIds"),
    category: str | None = Query(default=None),
) -> dict[str, Any]:
    return {"items": []}

@router.get("/sales_forecast", status_code=status.HTTP_200_OK)
def get_sales_forecast(
    db: Session = Depends(get_db),
    store_ids: str | None = Query(default=None, alias="storeIds"),
    category: str | None = Query(default=None),
) -> dict[str, Any]:
    return {"stores": []}

@router.get("/categories", status_code=status.HTTP_200_OK)
def get_categories(db: Session = Depends(get_db)) -> dict[str, Any]:
    # Placeholder con categorías más comunes conocidas; idealmente leer de catálogo.
    return {"categories": ["iPhone", "Samsung", "AirPods", "Accesorios"]}

@router.get("/alerts", status_code=status.HTTP_200_OK)
def get_alerts(
    db: Session = Depends(get_db),
    store_ids: str | None = Query(default=None, alias="storeIds"),
    category: str | None = Query(default=None),
) -> dict[str, Any]:
    # Estructura esperada: {"items": [{"level":"warning","message":"..."}], "total": 0}
    return {"items": [], "total": 0}

@router.get("/realtime", status_code=status.HTTP_200_OK)
def get_realtime(
    db: Session = Depends(get_db),
    store_ids: str | None = Query(default=None, alias="storeIds"),
    category: str | None = Query(default=None),
) -> dict[str, Any]:
    # Mini-resumen por sucursal para widget en tiempo real
    stores = crud.list_stores(db, limit=100, offset=0)
    items: list[dict[str, Any]] = []
    for s in stores:
        items.append(
            {
                "store_id": s.id,
                "store_name": s.name,
                "today_sales": 0,
                "trend": 0.0,
                "stock": 0,
            }
        )
    return {"stores": items}

# ---- Exportaciones (PDF / CSV) ---------------------------------------------

@router.get("/pdf", response_class=StreamingResponse)
def export_pdf(
    db: Session = Depends(get_db),
    x_reason: str | None = Header(default=None, convert_underscores=False, alias="X-Reason"),
    store_ids: str | None = Query(default=None, alias="storeIds"),
    category: str | None = Query(default=None),
) -> StreamingResponse:
    rotation: list[dict[str, Any]] = []
    aging: list[dict[str, Any]] = []
    forecast: list[dict[str, Any]] = []
    comparatives: list[dict[str, Any]] = []
    profit: list[dict[str, Any]] = []
    projection: list[dict[str, Any]] = []
    pdf_bytes = render_analytics_pdf(
        rotation=rotation,
        aging=aging,
        forecast=forecast,
        comparatives=comparatives,
        profit=profit,
        projection=projection,
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="softmobile_analytics.pdf"'},
    )

@router.get("/export.csv", response_class=StreamingResponse)
def export_csv(
    db: Session = Depends(get_db),
    x_reason: str | None = Header(default=None, convert_underscores=False, alias="X-Reason"),
    store_ids: str | None = Query(default=None, alias="storeIds"),
    category: str | None = Query(default=None),
) -> StreamingResponse:
    # CSV minimal compatible
    from io import StringIO
    import csv
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["section", "key", "value"])
    writer.writerow(["kpi", "total_items", 0])
    writer.writerow(["kpi", "low_stock", 0])
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="softmobile_analytics.csv"'},
    )
