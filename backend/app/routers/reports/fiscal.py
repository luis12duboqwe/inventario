from __future__ import annotations
import calendar
from datetime import date, datetime
from io import BytesIO
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app import crud, schemas
from backend.app.core.roles import ADMIN
from backend.app.database import get_db
from backend.app.routers.dependencies import require_reason_optional
from backend.app.security import require_roles
from backend.app.services import fiscal_books as fiscal_books_service
from .common import ensure_fiscal_reports_enabled

router = APIRouter(tags=["reportes"])


@router.get("/fiscal/books", response_model=schemas.FiscalBookReport)
def get_fiscal_book_report(
    book_type: schemas.FiscalBookType = Query(
        default=schemas.FiscalBookType.SALES),
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    export_format: Literal["json", "pdf", "xlsx", "xml"] = Query(
        default="json", alias="format"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    reason: str | None = Depends(require_reason_optional),
):
    ensure_fiscal_reports_enabled()
    try:
        start_date = date(year, month, 1)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Fecha inválida") from exc
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    filters = schemas.FiscalBookFilters(
        year=year, month=month, book_type=book_type)
    if book_type is schemas.FiscalBookType.SALES:
        sales = crud.list_sales(
            db,
            date_from=start_dt,
            date_to=end_dt,
            limit=None,
        )
        report = fiscal_books_service.build_sales_fiscal_book(sales, filters)
    else:
        purchases = crud.list_purchase_records_for_report(
            db,
            date_from=start_dt,
            date_to=end_dt,
        )
        report = fiscal_books_service.build_purchases_fiscal_book(
            purchases, filters)

    if export_format != "json" and not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Reason header requerido")

    if export_format == "json":
        return report

    filename_base = f"libro_{book_type.value}_{year}_{month:02d}"
    if export_format == "pdf":
        pdf_bytes = fiscal_books_service.render_fiscal_book_pdf(report)
        metadata = schemas.BinaryFileResponse(
            filename=f"{filename_base}.pdf",
            media_type="application/pdf",
        )
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type=metadata.media_type,
            headers=metadata.content_disposition(),
        )
    if export_format == "xlsx":
        workbook = fiscal_books_service.render_fiscal_book_excel(report)
        metadata = schemas.BinaryFileResponse(
            filename=f"{filename_base}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        return StreamingResponse(
            workbook,
            media_type=metadata.media_type,
            headers=metadata.content_disposition(),
        )
    if export_format == "xml":
        xml_buffer = fiscal_books_service.render_fiscal_book_xml(report)
        metadata = schemas.BinaryFileResponse(
            filename=f"{filename_base}.xml",
            media_type="application/xml",
        )
        return StreamingResponse(
            xml_buffer,
            media_type=metadata.media_type,
            headers=metadata.content_disposition(),
        )

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Formato de exportación no soportado")
