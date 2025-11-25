"""Endpoints públicos para entregar eventos vía webhooks corporativos."""

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db
from ..routers.dependencies import require_reason
from ..services.integrations import (
    IntegrationNotFoundError,
    IntegrationTokenInvalidError,
    integration_registry,
)

router = APIRouter(prefix="/integrations/hooks", tags=["integrations-webhooks"])

_ALLOWED_ENTITY_TYPES: tuple[str, ...] = (
    "sale",
    "transfer_order",
    "inventory",
)

_EVENT_PREFIX_MAP: dict[str, str] = {
    "sale": "sales.order",
    "transfer_order": "inventory.transfer",
    "inventory": "inventory.balance",
}


def _resolve_integration(slug: str, token: str | None) -> None:
    try:
        record = integration_registry.validate_token(slug, token or "")
    except IntegrationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integración no encontrada",
        ) from exc
    except IntegrationTokenInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de integración inválido",
        ) from exc

    if not record.supports_push:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La integración no admite webhooks",  # Mantener compatibilidad sin roles.
        )


def _entry_to_webhook_event(entry: models.SyncOutbox) -> schemas.IntegrationWebhookEvent:
    event_prefix = _EVENT_PREFIX_MAP.get(entry.entity_type, entry.entity_type)
    operation = (entry.operation or "update").lower()
    event_name = f"{event_prefix}.{operation}"

    payload = entry.payload if isinstance(entry.payload, dict) else {}

    return schemas.IntegrationWebhookEvent(
        id=entry.id,
        event=event_name,
        entity=entry.entity_type,
        entity_id=str(entry.entity_id),
        operation=entry.operation,
        payload=payload,
        version=int(entry.version or 1),
        status=entry.status,
        attempt_count=int(entry.attempt_count or 0),
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


@router.get(
    "/{slug}/events",
    response_model=list[schemas.IntegrationWebhookEvent],
    dependencies=[Depends(require_reason)],
)
def list_webhook_events(
    slug: str,
    status_filter: models.SyncOutboxStatus | None = Query(
        default=models.SyncOutboxStatus.PENDING
    ),
    limit: int = Query(default=50, ge=1, le=200),
    token: str | None = Header(default=None, alias="X-Integration-Token"),
    db: Session = Depends(get_db),
):
    _resolve_integration(slug, token)

    statuses: tuple[models.SyncOutboxStatus, ...] | None = None
    if status_filter is not None:
        statuses = (status_filter,)

    entries = crud.list_sync_outbox_by_entity(
        db,
        entity_types=_ALLOWED_ENTITY_TYPES,
        statuses=statuses,
        limit=limit,
        offset=0,
    )
    return [_entry_to_webhook_event(entry) for entry in entries]


@router.post(
    "/{slug}/events/{event_id}/ack",
    response_model=schemas.IntegrationWebhookAckResponse,
)
def acknowledge_webhook_event(
    slug: str,
    event_id: int,
    payload: schemas.IntegrationWebhookAckRequest,
    token: str | None = Header(default=None, alias="X-Integration-Token"),
    _reason: str = Depends(require_reason),
    db: Session = Depends(get_db),
):
    _resolve_integration(slug, token)

    entry = crud.get_sync_outbox_entry(
        db, entry_id=event_id, entity_types=_ALLOWED_ENTITY_TYPES
    )
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evento no encontrado"
        )

    if payload.status == "sent":
        updated = crud.mark_outbox_entries_sent(db, [entry.id], performed_by_id=None)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Evento no encontrado"
            )
        entry = updated[0]
    else:
        entry = crud.mark_outbox_entry_failed(
            db,
            entry_id=entry.id,
            error_message=payload.error_message,
            performed_by_id=None,
        )
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Evento no encontrado"
            )

    return schemas.IntegrationWebhookAckResponse(
        id=entry.id,
        status=entry.status,
        attempts=int(entry.attempt_count or 0),
        error_message=entry.error_message,
    )


__all__ = ["router"]
