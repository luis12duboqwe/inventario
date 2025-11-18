"""Endpoints para administrar configuración centralizada."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..config import settings
from ..core.roles import ADMIN
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services import configuration as configuration_service

router = APIRouter(prefix="/configuration", tags=["configuración"])


@router.get(
    "/overview",
    response_model=schemas.ConfigurationOverview,
    dependencies=[Depends(require_roles(ADMIN))],
)
def read_configuration_overview(
    include_inactive: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
) -> schemas.ConfigurationOverview:
    _ = current_user
    return configuration_service.get_overview(
        db, include_inactive=include_inactive
    )


@router.get(
    "/rates",
    response_model=list[schemas.ConfigurationRateResponse],
    dependencies=[Depends(require_roles(ADMIN))],
)
def list_rates(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
) -> list[schemas.ConfigurationRateResponse]:
    _ = current_user
    return configuration_service.list_config_rates(
        db, include_inactive=include_inactive
    )


@router.post(
    "/rates",
    response_model=schemas.ConfigurationRateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_rate(
    payload: schemas.ConfigurationRateCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(ADMIN)),
) -> schemas.ConfigurationRateResponse:
    _ = (current_user, reason)
    try:
        return configuration_service.create_config_rate(
            db, payload, performed_by_id=current_user.id if current_user else None
        )
    except ValueError as exc:
        if str(exc) == "config_rate_conflict":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una tasa con el mismo identificador.",
            ) from exc
        raise


@router.put(
    "/rates/{rate_id}",
    response_model=schemas.ConfigurationRateResponse,
)
def update_rate(
    payload: schemas.ConfigurationRateUpdate,
    rate_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(ADMIN)),
) -> schemas.ConfigurationRateResponse:
    _ = (current_user, reason)
    try:
        return configuration_service.update_config_rate(
            db,
            rate_id,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        if str(exc) == "config_rate_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La tasa solicitada no existe.",
            ) from exc
        raise


@router.get(
    "/xml-templates",
    response_model=list[schemas.ConfigurationXmlTemplateResponse],
    dependencies=[Depends(require_roles(ADMIN))],
)
def list_xml_templates(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
) -> list[schemas.ConfigurationXmlTemplateResponse]:
    _ = current_user
    return configuration_service.list_config_xml_templates(
        db, include_inactive=include_inactive
    )


@router.post(
    "/xml-templates",
    response_model=schemas.ConfigurationXmlTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_xml_template(
    payload: schemas.ConfigurationXmlTemplateCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(ADMIN)),
) -> schemas.ConfigurationXmlTemplateResponse:
    _ = (current_user, reason)
    try:
        return configuration_service.create_config_xml_template(
            db,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
    except ValueError as exc:
        if str(exc) == "config_xml_conflict":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una plantilla con el mismo código.",
            ) from exc
        raise


@router.put(
    "/xml-templates/{template_id}",
    response_model=schemas.ConfigurationXmlTemplateResponse,
)
def update_xml_template(
    payload: schemas.ConfigurationXmlTemplateUpdate,
    template_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(ADMIN)),
) -> schemas.ConfigurationXmlTemplateResponse:
    _ = (current_user, reason)
    try:
        return configuration_service.update_config_xml_template(
            db,
            template_id,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        if str(exc) == "config_xml_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La plantilla solicitada no existe.",
            ) from exc
        raise


@router.get(
    "/parameters",
    response_model=list[schemas.ConfigurationParameterResponse],
    dependencies=[Depends(require_roles(ADMIN))],
)
def list_parameters(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
) -> list[schemas.ConfigurationParameterResponse]:
    _ = current_user
    return configuration_service.list_config_parameters(
        db, include_inactive=include_inactive
    )


@router.post(
    "/parameters",
    response_model=schemas.ConfigurationParameterResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_parameter(
    payload: schemas.ConfigurationParameterCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(ADMIN)),
) -> schemas.ConfigurationParameterResponse:
    _ = (current_user, reason)
    try:
        return configuration_service.create_config_parameter(
            db,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
    except ValueError as exc:
        if str(exc) == "config_parameter_conflict":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un parámetro con la misma clave.",
            ) from exc
        raise


@router.put(
    "/parameters/{parameter_id}",
    response_model=schemas.ConfigurationParameterResponse,
)
def update_parameter(
    payload: schemas.ConfigurationParameterUpdate,
    parameter_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(ADMIN)),
) -> schemas.ConfigurationParameterResponse:
    _ = (current_user, reason)
    try:
        return configuration_service.update_config_parameter(
            db,
            parameter_id,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        if str(exc) == "config_parameter_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El parámetro solicitado no existe.",
            ) from exc
        raise


@router.post(
    "/sync",
    response_model=schemas.ConfigurationSyncResult,
)
def synchronize_from_yaml(
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(ADMIN)),
) -> schemas.ConfigurationSyncResult:
    _ = (current_user, reason)
    if not settings.config_sync_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La sincronización sin despliegue está desactivada.",
        )
    try:
        result = configuration_service.synchronize_from_yaml(
            db, settings.config_sync_path
        )
        crud.log_audit_event(
            db,
            action="configuration_sync",
            entity_type="config_sync",
            entity_id="yaml",
            performed_by_id=current_user.id if current_user else None,
            details={
                "archivos_procesados": result.processed_files,
                "tasas_activadas": result.rates_activated,
                "tasas_desactivadas": result.rates_deactivated,
                "plantillas_activadas": result.templates_activated,
                "plantillas_desactivadas": result.templates_deactivated,
                "parametros_activados": result.parameters_activated,
                "parametros_desactivados": result.parameters_deactivated,
            },
        )
        return result
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el directorio de sincronización configurado.",
        ) from exc
    except ValueError as exc:
        if str(exc).startswith("config_sync_yaml_invalid"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Los archivos YAML contienen errores de sintaxis o estructura.",
            ) from exc
        raise
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Los archivos YAML contienen datos inválidos.",
        ) from exc

