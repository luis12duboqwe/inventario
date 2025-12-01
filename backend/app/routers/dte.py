"""Endpoints para gestionar Documentos Tributarios Electrónicos (DTE)."""
from __future__ import annotations

from typing import Iterable

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..core.config import settings as core_settings
from ..core.roles import GESTION_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services.dte import generate_document, record_dispatch, register_acknowledgement

router = APIRouter(prefix="/dte", tags=["dte"])


def _ensure_dte_enabled() -> None:
    if not core_settings.enable_dte:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La funcionalidad DTE no está disponible en este entorno.",
        )


def _map_authorization_error(exc: ValueError) -> None:
    message = str(exc)
    if message == "dte_authorization_conflict":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una autorización activa para esa serie y rango.",
        ) from exc
    if message == "dte_authorization_inactive":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La autorización seleccionada está inactiva.",
        ) from exc
    if message == "dte_authorization_expired":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La autorización seleccionada se encuentra vencida.",
        ) from exc
    if message == "dte_authorization_store_mismatch":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La autorización no aplica para la sucursal de la venta.",
        ) from exc
    if message == "dte_authorization_exhausted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El rango autorizado ya fue agotado.",
        ) from exc
    raise exc


def _build_document_response(document: models.DTEDocument) -> schemas.DTEDocumentResponse:
    events = getattr(document, "events", [])
    setattr(document, "events", list(events))
    queue_entries = getattr(document, "dispatch_entries", [])
    setattr(document, "queue", list(queue_entries))
    return schemas.DTEDocumentResponse.model_validate(document, from_attributes=True)


@router.get(
    "/authorizations",
    response_model=list[schemas.DTEAuthorizationResponse],
)
def list_dte_authorizations_endpoint(
    store_id: int | None = Query(default=None, ge=1),
    document_type: str | None = Query(default=None, min_length=2, max_length=30),
    active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> list[schemas.DTEAuthorizationResponse]:
    _ensure_dte_enabled()
    authorizations = crud.list_dte_authorizations(
        db,
        store_id=store_id,
        document_type=document_type,
        active=active,
    )
    return [
        schemas.DTEAuthorizationResponse.model_validate(auth, from_attributes=True)
        for auth in authorizations
    ]


@router.post(
    "/authorizations",
    response_model=schemas.DTEAuthorizationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_dte_authorization_endpoint(
    payload: schemas.DTEAuthorizationCreate,
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.DTEAuthorizationResponse:
    _ensure_dte_enabled()
    try:
        authorization = crud.create_dte_authorization(db, payload)
    except ValueError as exc:
        _map_authorization_error(exc)
    return schemas.DTEAuthorizationResponse.model_validate(
        authorization, from_attributes=True
    )


@router.put(
    "/authorizations/{authorization_id}",
    response_model=schemas.DTEAuthorizationResponse,
)
def update_dte_authorization_endpoint(
    payload: schemas.DTEAuthorizationUpdate,
    authorization_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.DTEAuthorizationResponse:
    _ensure_dte_enabled()
    try:
        authorization = crud.update_dte_authorization(db, authorization_id, payload)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Autorización no encontrada.",
        ) from exc
    return schemas.DTEAuthorizationResponse.model_validate(
        authorization, from_attributes=True
    )


@router.post(
    "/documents/generate",
    response_model=schemas.DTEDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_dte_document_endpoint(
    payload: schemas.DTEGenerationRequest,
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.DTEDocumentResponse:
    _ensure_dte_enabled()
    try:
        document = generate_document(
            db,
            payload,
            performed_by_id=getattr(current_user, "id", None),
        )
    except LookupError as exc:
        message = str(exc)
        detail = "Recurso no encontrado"
        if message == "dte_authorization_not_found":
            detail = "La autorización indicada no existe."
        elif message == "sale_not_found":
            detail = "La venta indicada no existe."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
    except ValueError as exc:
        _map_authorization_error(exc)
    return _build_document_response(document)


@router.get(
    "/documents",
    response_model=list[schemas.DTEDocumentResponse],
)
def list_dte_documents_endpoint(
    store_id: int | None = Query(default=None, ge=1),
    sale_id: int | None = Query(default=None, ge=1),
    status_filter: models.DTEStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> list[schemas.DTEDocumentResponse]:
    _ensure_dte_enabled()
    documents = crud.list_dte_documents(
        db,
        store_id=store_id,
        sale_id=sale_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return [_build_document_response(doc) for doc in documents]


@router.get(
    "/documents/{document_id}",
    response_model=schemas.DTEDocumentResponse,
)
def get_dte_document_endpoint(
    document_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.DTEDocumentResponse:
    _ensure_dte_enabled()
    try:
        document = crud.get_dte_document(db, document_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado.",
        ) from exc
    return _build_document_response(document)


@router.post(
    "/documents/{document_id}/send",
    response_model=schemas.DTEDocumentResponse,
)
def send_dte_document_endpoint(
    payload: schemas.DTEDispatchRequest,
    document_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.DTEDocumentResponse:
    _ensure_dte_enabled()
    try:
        document = crud.get_dte_document(db, document_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado.",
        ) from exc
    record_dispatch(
        db,
        document=document,
        payload=payload,
        performed_by_id=getattr(current_user, "id", None),
    )
    db.refresh(document)
    return _build_document_response(document)


@router.post(
    "/documents/{document_id}/ack",
    response_model=schemas.DTEDocumentResponse,
)
def acknowledge_dte_document_endpoint(
    payload: schemas.DTEAckRegistration,
    document_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.DTEDocumentResponse:
    _ensure_dte_enabled()
    try:
        document = crud.get_dte_document(db, document_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado.",
        ) from exc
    updated_document = register_acknowledgement(
        db,
        document=document,
        payload=payload,
        performed_by_id=getattr(current_user, "id", None),
    )
    return _build_document_response(updated_document)


@router.get(
    "/queue",
    response_model=list[schemas.DTEDispatchQueueEntryResponse],
)
def list_dte_queue_endpoint(
    status_filter: models.DTEDispatchStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> list[schemas.DTEDispatchQueueEntryResponse]:
    _ensure_dte_enabled()
    statuses: Iterable[models.DTEDispatchStatus] | None = None
    if status_filter is not None:
        statuses = [status_filter]
    entries = crud.list_dte_dispatch_queue(db, statuses=statuses)
    return [
        schemas.DTEDispatchQueueEntryResponse.model_validate(entry, from_attributes=True)
        for entry in entries
    ]


__all__ = ["router"]
