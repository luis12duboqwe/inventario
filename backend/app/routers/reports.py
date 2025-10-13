"""Reportes consolidados y bitácoras."""
from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..core.roles import AUDITORIA_ROLES, REPORTE_ROLES
from ..database import get_db
from ..security import require_roles
from ..services import backups as backup_services

router = APIRouter(prefix="/reports", tags=["reportes"])


@router.get("/audit", response_model=list[schemas.AuditLogResponse])
def audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*AUDITORIA_ROLES)),
):
    return crud.list_audit_logs(db, limit=limit)


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
