"""Endpoints para la bitácora de auditoría de UI."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.orm import Session

from .. import schemas
from ..core.roles import ADMIN
from ..database import get_db
from ..security import require_roles
from ..services import audit_ui as audit_ui_service
from ..usecases import audit_ui as audit_ui_usecases

router = APIRouter(prefix="/api/audit/ui", tags=["auditoría"])


@router.post(
    "/bulk",
    response_model=schemas.AuditUIBulkResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(ADMIN))],
)
def bulk_insert_audit_ui(
    payload: schemas.AuditUIBulkRequest,
    db: Session = Depends(get_db),
) -> schemas.AuditUIBulkResponse:
    """Inserta un lote de eventos de auditoría de la interfaz."""

    # // [PACK32-33-BE] Inserción masiva para sincronizar la cola local del frontend.
    inserted = audit_ui_usecases.create_entries(db, items=payload.items)
    return schemas.AuditUIBulkResponse(inserted=inserted)


@router.get(
    "",
    response_model=schemas.AuditUIListResponse,
    dependencies=[Depends(require_roles(ADMIN))],
)
def list_audit_ui(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    date_from: datetime | date | None = Query(default=None, alias="from"),
    date_to: datetime | date | None = Query(default=None, alias="to"),
    user_id: str | None = Query(default=None, alias="userId", max_length=120),
    module: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
) -> schemas.AuditUIListResponse:
    """Lista eventos almacenados con filtros y paginación sencilla."""

    entries, total = audit_ui_usecases.list_entries(
        db,
        limit=limit,
        offset=offset,
        date_from=date_from,
        date_to=date_to,
        user_id=user_id,
        module=module,
        range_normalizer=audit_ui_service.normalize_range,
    )
    has_more = offset + limit < total
    items = [schemas.AuditUIRecord.model_validate(entry) for entry in entries]
    return schemas.AuditUIListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.get(
    "/export",
    dependencies=[Depends(require_roles(ADMIN))],
)
def export_audit_ui(
    format: schemas.AuditUIExportFormat = Query(
        default=schemas.AuditUIExportFormat.JSON),
    date_from: datetime | date | None = Query(default=None, alias="from"),
    date_to: datetime | date | None = Query(default=None, alias="to"),
    user_id: str | None = Query(default=None, alias="userId", max_length=120),
    module: str | None = Query(default=None, max_length=80),
    limit: int | None = Query(default=None, ge=1, le=10000),
    db: Session = Depends(get_db),
) -> Response:
    """Exporta la bitácora como CSV o JSON listo para descarga."""

    payload = audit_ui_usecases.export_entries(
        db,
        export_format=format,
        date_from=date_from,
        date_to=date_to,
        user_id=user_id,
        module=module,
        limit=limit,
        range_normalizer=audit_ui_service.normalize_range,
        serializer=audit_ui_service.serialize_entries,
    )

    filename = f"audit_ui.{format.value}"
    if format is schemas.AuditUIExportFormat.CSV:
        return PlainTextResponse(
            payload,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    return Response(
        content=payload,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


__all__ = ["router"]
