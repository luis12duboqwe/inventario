"""Rutas para la validación avanzada de importaciones de inventario."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..core.roles import GESTION_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services import import_validation as import_validation_service

router = APIRouter(prefix="/validacion", tags=["validación importaciones"])


def _map_validation(validation: models.ImportValidation) -> schemas.ImportValidationDetail:
    device_payload = None
    if validation.device is not None:
        store_name = validation.device.store.name if validation.device.store is not None else ""
        device_payload = schemas.ImportValidationDevice(
            id=validation.device.id,
            store_id=validation.device.store_id,
            store_name=store_name,
            sku=validation.device.sku,
            name=validation.device.name,
            imei=validation.device.imei,
            serial=validation.device.serial,
            marca=validation.device.marca,
            modelo=validation.device.modelo,
        )
    return schemas.ImportValidationDetail(
        id=validation.id,
        producto_id=validation.producto_id,
        tipo=validation.tipo,
        severidad=validation.severidad,
        descripcion=validation.descripcion,
        fecha=validation.fecha,
        corregido=validation.corregido,
        device=device_payload,
    )


@router.get(
    "/pendientes",
    response_model=list[schemas.ImportValidationDetail],
    status_code=status.HTTP_200_OK,
)
def list_pending_validations(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> list[schemas.ImportValidationDetail]:
    validations = crud.list_import_validation_details(
        db, corregido=False, limit=limit, offset=offset
    )
    return [_map_validation(validation) for validation in validations]


@router.patch(
    "/{validation_id}/corregir",
    response_model=schemas.ImportValidation,
    status_code=status.HTTP_200_OK,
)
def mark_validation_corrected(
    validation_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.ImportValidation:
    try:
        validation = crud.mark_import_validation_corrected(db, validation_id)
    except LookupError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="validacion_no_encontrada") from exc
    return schemas.ImportValidation.model_validate(validation)


@router.get(
    "/reporte",
    response_model=schemas.ImportValidationSummary,
    status_code=status.HTTP_200_OK,
)
def retrieve_validation_report(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.ImportValidationSummary:
    return crud.get_import_validation_report(db)


@router.get(
    "/exportar",
    status_code=status.HTTP_200_OK,
    response_model=schemas.BinaryFileResponse,
)
def export_validation_report(
    formato: Literal["excel", "pdf"] = Query(default="excel"),
    incluir_corregidas: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> StreamingResponse:
    limit = None if incluir_corregidas else 500
    validations = crud.list_import_validation_details(
        db,
        corregido=None if incluir_corregidas else False,
        limit=limit,
    )
    summary = crud.get_import_validation_report(db)
    if formato == "pdf":
        buffer = import_validation_service.export_validations_to_pdf(validations, summary)
        metadata = schemas.BinaryFileResponse(
            filename="validaciones_importacion.pdf",
            media_type="application/pdf",
        )
    else:
        buffer = import_validation_service.export_validations_to_excel(validations, summary)
        metadata = schemas.BinaryFileResponse(
            filename="validaciones_importacion.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    return StreamingResponse(buffer, media_type=metadata.media_type, headers=metadata.content_disposition())
