from __future__ import annotations
import csv
from datetime import date, datetime, timedelta, timezone
from io import StringIO
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app import crud, schemas
from backend.app.core.roles import ADMIN
from backend.app.database import get_db
from backend.app.security import require_roles
from .common import ensure_analytics_enabled, normalize_sales_range, format_range_value

router = APIRouter(tags=["reportes"])


@router.get(
    "/sales/summary",
    response_model=schemas.SalesSummaryReport
)
def get_sales_summary_report(
    date_from: datetime | date | None = Query(default=None, alias="from"),
    date_to: datetime | date | None = Query(default=None, alias="to"),
    branch_id: int | None = Query(default=None, alias="branchId", ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    ensure_analytics_enabled()
    normalized_from, normalized_to = normalize_sales_range(date_from, date_to)
    if normalized_from and normalized_to and normalized_from >= normalized_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El rango de fechas es inválido.",
        )
    return crud.build_sales_summary_report(
        db,
        date_from=normalized_from,
        date_to=normalized_to,
        store_id=branch_id,
    )


@router.get(
    "/sales/by-product",
    response_model=list[schemas.SalesByProductItem]
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
    ensure_analytics_enabled()
    normalized_from, normalized_to = normalize_sales_range(date_from, date_to)
    if normalized_from and normalized_to and normalized_from >= normalized_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
        writer.writerow(["SKU", "Producto", "Cantidad",
                        "Ventas brutas", "Ventas netas"])
        for item in items:
            writer.writerow([
                item.sku,
                item.name,
                item.quantity,
                f"{item.gross:.2f}",
                f"{item.net:.2f}",
            ])
        filename_parts: list[str] = []
        from_label = format_range_value(date_from)
        to_label = format_range_value(date_to)
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


@router.get(
    "/cash-close",
    response_model=schemas.CashCloseReport
)
def get_cash_close_report(
    target_date: date | None = Query(default=None, alias="date"),
    branch_id: int | None = Query(default=None, alias="branchId", ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    ensure_analytics_enabled()
    report_date = target_date or datetime.now(timezone.utc).date()
    start_of_day = datetime.combine(report_date, datetime.min.time())
    end_of_day = start_of_day + timedelta(days=1)
    return crud.build_cash_close_report(
        db,
        date_from=start_of_day,
        date_to=end_of_day,
        store_id=branch_id,
    )
