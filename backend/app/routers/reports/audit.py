from __future__ import annotations
from datetime import date, datetime
from io import BytesIO

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app import crud, schemas
from backend.app.core.roles import ADMIN
from backend.app.database import get_db
from backend.app.routers.dependencies import require_reason
from backend.app.security import require_roles
from backend.app.services import audit as audit_service
from backend.app.utils import audit as audit_utils
from backend.schemas.common import Page, PageParams

router = APIRouter(tags=["reportes"])


@router.get("/audit", response_model=Page[schemas.AuditLogResponse])
def audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action: str | None = Query(default=None, max_length=120),
    entity_type: str | None = Query(default=None, max_length=80),
    module: str | None = Query(default=None, max_length=80),
    performed_by_id: int | None = Query(default=None, ge=1),
    severity: audit_utils.AuditSeverity | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    pagination: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
) -> Page[schemas.AuditLogResponse]:
    page_offset = pagination.offset if (
        pagination.page > 1 and offset == 0) else offset
    page_size = min(pagination.size, limit)
    total = crud.count_audit_logs(
        db,
        action=action,
        entity_type=entity_type,
        module=module,
        performed_by_id=performed_by_id,
        severity=severity,
        date_from=date_from,
        date_to=date_to,
    )
    logs = crud.list_audit_logs(
        db,
        limit=page_size,
        offset=page_offset,
        action=action,
        entity_type=entity_type,
        module=module,
        performed_by_id=performed_by_id,
        severity=severity,
        date_from=date_from,
        date_to=date_to,
    )
    page_number = (
        pagination.page if offset == 0 else max(
            1, (page_offset // page_size) + 1)
    )
    return Page.from_items(logs, page=page_number, size=page_size, total=total)


@router.get("/audit/pdf", response_model=schemas.BinaryFileResponse)
def audit_logs_pdf(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action: str | None = Query(default=None, max_length=120),
    entity_type: str | None = Query(default=None, max_length=80),
    module: str | None = Query(default=None, max_length=80),
    performed_by_id: int | None = Query(default=None, ge=1),
    severity: audit_utils.AuditSeverity | None = Query(default=None),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    _reason: str = Depends(require_reason),
):
    logs = crud.list_audit_logs(
        db,
        limit=limit,
        offset=offset,
        action=action,
        entity_type=entity_type,
        module=module,
        performed_by_id=performed_by_id,
        severity=severity,
        date_from=date_from,
        date_to=date_to,
    )
    summary = audit_utils.summarize_alerts(logs)
    filters: dict[str, str] = {}
    if action:
        filters["Acción"] = action
    if entity_type:
        filters["Tipo de entidad"] = entity_type
    if module:
        filters["Módulo"] = module
    if performed_by_id is not None:
        filters["Usuario"] = str(performed_by_id)
    if severity:
        filters["Severidad"] = severity
    if date_from:
        filters["Desde"] = str(date_from)
    if date_to:
        filters["Hasta"] = str(date_to)
    pdf_bytes = audit_service.render_audit_pdf(
        logs, filters=filters, alerts=summary)
    buffer = BytesIO(pdf_bytes)
    metadata = schemas.BinaryFileResponse(
        filename="auditoria_softmobile.pdf",
        media_type="application/pdf",
    )
    return StreamingResponse(
        buffer,
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )
