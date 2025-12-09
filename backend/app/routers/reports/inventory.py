from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app import crud, schemas
from backend.app.core.roles import ADMIN, GERENTE
from backend.app.database import get_db
from backend.app.routers.dependencies import require_reason
from backend.app.security import require_roles
from backend.app.services import inventory_reports

router = APIRouter(prefix="/inventory", tags=["reportes", "inventario"])


@router.get("/pdf")
def export_inventory_pdf(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN, GERENTE)),
    _reason: str = Depends(require_reason),
):
    report = crud.get_inventory_current_report(db)
    pdf_bytes = inventory_reports.render_inventory_current_pdf(report)
    metadata = schemas.BinaryFileResponse(
        filename="softmobile_inventario.pdf",
        media_type="application/pdf",
    )
    buffer = BytesIO(pdf_bytes)
    return StreamingResponse(
        buffer,
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )
