"""Endpoints dedicados a las importaciones de inventario."""
from __future__ import annotations

import json

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.schemas.common import Page, PageParams

from .. import crud, schemas
from ..core.roles import MOVEMENT_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services import inventory_import, inventory_smart_import

router = APIRouter(prefix="/inventory", tags=["inventario"])


@router.post(
    "/import/smart",
    response_model=schemas.InventorySmartImportResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
async def smart_import_inventory(
    file: UploadFile = File(...),
    commit: bool = Form(default=False),
    overrides: str | None = Form(default=None),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
):
    """Procesa la importación inteligente permitiendo vista previa o confirmación."""

    try:
        parsed_overrides = json.loads(overrides) if overrides else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="overrides_invalid",
        ) from exc

    if not isinstance(parsed_overrides, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="overrides_invalid",
        )

    overrides_cast = {
        str(key): str(value) for key, value in parsed_overrides.items()
    }

    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="archivo_vacio",
        )

    try:
        response = inventory_smart_import.process_smart_import(
            db,
            file_bytes=contents,
            filename=file.filename or "importacion.xlsx",
            commit=commit,
            overrides=overrides_cast,
            performed_by_id=current_user.id if current_user else None,
            username=getattr(current_user, "username", None),
            reason=reason,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return response


@router.get(
    "/import/smart/history",
    response_model=Page[schemas.InventoryImportHistoryEntry],
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def list_import_history(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pagination: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> Page[schemas.InventoryImportHistoryEntry]:
    """Lista el historial de importaciones inteligentes paginadas."""

    page_offset = (
        pagination.offset if (pagination.page > 1 and offset == 0) else offset
    )
    page_size = min(pagination.size, limit)
    total = crud.count_inventory_import_history(db)
    records = crud.list_inventory_import_history(
        db, limit=page_size, offset=page_offset
    )
    items = [
        schemas.InventoryImportHistoryEntry.model_validate(record)
        for record in records
    ]
    return Page.from_items(items, page=pagination.page, size=page_size, total=total)


@router.post(
    "/stores/{store_id}/devices/import",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.InventoryImportSummary,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
async def import_devices(
    store_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
):
    """Importa dispositivos desde CSV clásico para la tienda indicada."""

    if file.content_type not in {
        "text/csv",
        "application/vnd.ms-excel",
        "application/octet-stream",
        None,
    }:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Formato no soportado. Carga un archivo CSV.",
        )

    content = await file.read()
    try:
        summary = inventory_import.import_devices_from_csv(
            db,
            store_id,
            content,
            performed_by_id=current_user.id if current_user else None,
        )
    except (ValueError, ValidationError) as exc:
        message = str(exc)
        if isinstance(exc, ValidationError):
            detail = {
                "code": "csv_import_error",
                "message": "El archivo contiene datos inválidos.",
            }
        elif message.startswith("csv_missing_columns"):
            missing = message.split(":", maxsplit=1)[1]
            detail = {
                "code": "csv_missing_columns",
                "message": (
                    "El archivo debe incluir las columnas requeridas: "
                    f"{missing}"
                ),
            }
        elif message == "csv_missing_header":
            detail = {
                "code": "csv_missing_header",
                "message": "No se encontró encabezado en el archivo.",
            }
        elif message == "csv_encoding_error":
            detail = {
                "code": "csv_encoding_error",
                "message": (
                    "No fue posible leer el archivo. Usa codificación UTF-8."
                ),
            }
        else:
            detail = {
                "code": "csv_import_error",
                "message": "El archivo contiene datos inválidos.",
            }
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=detail
        ) from exc

    summary_payload = schemas.InventoryImportSummary(**summary)
    if summary_payload.errors:
        detail = {
            "code": "csv_import_error",
            "message": "El archivo contiene datos inválidos.",
            "errors": [error.model_dump() for error in summary_payload.errors],
        }
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=detail
        )

    return summary_payload
