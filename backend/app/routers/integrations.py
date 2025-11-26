"""Endpoints para gestionar integraciones externas."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from .. import schemas
from ..core.roles import ADMIN
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services.integrations import (
    IntegrationNotFoundError,
    IntegrationRecord,
    integration_registry,
)

INTEGRATION_ADMIN_ROLES = (ADMIN,)

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _resolve_credential(record: IntegrationRecord) -> schemas.IntegrationCredentialInfo:
    if record.credential is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Integración sin credencial activa",
        )
    credential = record.credential
    return schemas.IntegrationCredentialInfo(
        token_hint=credential.token_hint,
        rotated_at=credential.rotated_at,
        expires_at=credential.expires_at,
    )


def _resolve_health(record: IntegrationRecord) -> schemas.IntegrationHealthStatus:
    health = record.health
    return schemas.IntegrationHealthStatus(
        status=health.status,
        checked_at=health.checked_at,
        message=health.message,
    )


def _record_to_summary(record: IntegrationRecord) -> schemas.IntegrationProviderSummary:
    return schemas.IntegrationProviderSummary(
        slug=record.slug,
        name=record.name,
        category=record.category,
        status=record.status,
        supports_push=record.supports_push,
        supports_pull=record.supports_pull,
        events=record.events,
        documentation_url=record.documentation_url,
        credential=_resolve_credential(record),
        health=_resolve_health(record),
    )


def _record_to_detail(record: IntegrationRecord) -> schemas.IntegrationProviderDetail:
    return schemas.IntegrationProviderDetail(
        slug=record.slug,
        name=record.name,
        category=record.category,
        status=record.status,
        auth_type=record.auth_type,
        description=record.description,
        supports_push=record.supports_push,
        supports_pull=record.supports_pull,
        events=record.events,
        documentation_url=record.documentation_url,
        features=record.features,
        setup_instructions=record.setup_instructions,
        credential=_resolve_credential(record),
        health=_resolve_health(record),
    )


@router.get(
    "/",
    response_model=list[schemas.IntegrationProviderSummary],
    dependencies=[Depends(require_roles(*INTEGRATION_ADMIN_ROLES))],
)
def list_integrations_endpoint() -> list[schemas.IntegrationProviderSummary]:
    """Devuelve todas las integraciones registradas."""

    records = integration_registry.list_providers()
    return [_record_to_summary(record) for record in records]


@router.get(
    "/{slug}",
    response_model=schemas.IntegrationProviderDetail,
    dependencies=[Depends(require_roles(*INTEGRATION_ADMIN_ROLES))],
)
def get_integration_detail_endpoint(slug: str) -> schemas.IntegrationProviderDetail:
    """Entrega la ficha completa de una integración específica."""

    try:
        record = integration_registry.get_provider(slug)
    except IntegrationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integración no encontrada",
        ) from exc
    return _record_to_detail(record)


@router.post(
    "/{slug}/rotate",
    response_model=schemas.IntegrationRotateSecretResponse,
    dependencies=[Depends(require_roles(*INTEGRATION_ADMIN_ROLES))],
)
def rotate_integration_secret_endpoint(
    slug: str,
    _reason: str = Depends(require_reason),
) -> schemas.IntegrationRotateSecretResponse:
    """Genera un nuevo token API para la integración solicitada."""

    try:
        record, token = integration_registry.rotate_token(slug)
    except IntegrationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integración no encontrada",
        ) from exc
    return schemas.IntegrationRotateSecretResponse(
        slug=record.slug,
        token=token,
        credential=_resolve_credential(record),
    )


@router.post(
    "/{slug}/health",
    response_model=schemas.IntegrationHealthStatus,
    dependencies=[Depends(require_roles(*INTEGRATION_ADMIN_ROLES))],
)
def update_integration_health_endpoint(
    slug: str,
    payload: schemas.IntegrationHealthUpdateRequest,
    _reason: str = Depends(require_reason),
) -> schemas.IntegrationHealthStatus:
    """Actualiza el estado de salud reportado por los monitores externos."""

    try:
        record = integration_registry.update_health(
            slug,
            status=payload.status,
            message=payload.message,
        )
    except IntegrationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integración no encontrada",
        ) from exc
    return _resolve_health(record)


__all__ = ["router"]
