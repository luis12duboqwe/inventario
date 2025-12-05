from __future__ import annotations
from datetime import date
from io import BytesIO
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app import crud, schemas
from backend.app.core.roles import ADMIN
from backend.app.database import get_db
from backend.app.routers.dependencies import require_reason
from backend.app.security import require_roles
from backend.app.services import customer_reports

router = APIRouter(tags=["reportes"])


@router.get("/customers/portfolio", response_model=schemas.CustomerPortfolioReport)
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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
