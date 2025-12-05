from __future__ import annotations
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models import SyncOutboxStatus


class IntegrationCredentialInfo(BaseModel):
    """Resumen de credenciales expuestas a los administradores."""

    token_hint: str = Field(
        ...,
        min_length=4,
        max_length=8,
        description="Últimos caracteres visibles del token activo.",
    )
    rotated_at: datetime = Field(
        ...,
        description="Marca temporal en UTC de la última rotación del token.",
    )
    expires_at: datetime = Field(
        ...,
        description="Fecha en UTC en la que expira el token vigente.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token_hint": "a1B3",
                "rotated_at": "2025-11-06T04:00:00+00:00",
                "expires_at": "2026-02-04T04:00:00+00:00",
            }
        }
    )


class IntegrationHealthStatus(BaseModel):
    """Estado de salud reportado por los monitores corporativos."""

    status: str = Field(
        ...,
        min_length=2,
        max_length=40,
        description="Estado declarado (por ejemplo: operational, degraded, offline).",
    )
    checked_at: datetime | None = Field(
        default=None,
        description="Marca temporal en UTC del último chequeo exitoso.",
    )
    message: str | None = Field(
        default=None,
        max_length=200,
        description="Mensaje opcional con detalles del monitoreo.",
    )


class IntegrationProviderSummary(BaseModel):
    """Información general visible en el catálogo de integraciones."""

    slug: str = Field(
        ...,
        min_length=3,
        max_length=60,
        description="Identificador corto de la integración.",
    )
    name: str = Field(
        ...,
        min_length=3,
        max_length=120,
        description="Nombre comercial del conector externo.",
    )
    category: str = Field(
        ...,
        min_length=3,
        max_length=60,
        description="Categoría operativa del conector (analítica, automatización, etc.).",
    )
    status: str = Field(
        ...,
        min_length=2,
        max_length=40,
        description="Estado corporativo actual (active, beta, deprecated, etc.).",
    )
    supports_push: bool = Field(
        default=False,
        description="Indica si Softmobile envía eventos al conector mediante webhooks.",
    )
    supports_pull: bool = Field(
        default=True,
        description="Indica si el conector consulta datos directamente de la API.",
    )
    events: list[str] = Field(
        default_factory=list,
        description="Eventos estándar publicados para la integración.",
    )
    documentation_url: str | None = Field(
        default=None,
        description="Enlace de referencia con la documentación técnica del conector.",
    )
    credential: IntegrationCredentialInfo
    health: IntegrationHealthStatus

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "slug": "zapier",
                "name": "Zapier Inventory Bridge",
                "category": "automatizacion",
                "status": "active",
                "supports_push": True,
                "supports_pull": True,
                "events": [
                    "inventory.device.updated",
                    "sales.order.completed",
                ],
                "documentation_url": "https://docs.softmobile.mx/integraciones/zapier",
                "credential": {
                    "token_hint": "XyZ9",
                    "rotated_at": "2025-10-01T06:00:00+00:00",
                    "expires_at": "2025-12-30T06:00:00+00:00",
                },
                "health": {
                    "status": "operational",
                    "checked_at": "2025-11-05T05:00:00+00:00",
                    "message": "Webhook confirmó respuesta 200 en 120 ms",
                },
            }
        }
    )


class IntegrationProviderDetail(IntegrationProviderSummary):
    """Ficha extendida con capacidades y pasos de despliegue."""

    auth_type: str = Field(
        ...,
        min_length=3,
        max_length=40,
        description="Método de autenticación utilizado (api_key, oauth2, etc.).",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Descripción funcional de la integración.",
    )
    features: dict[str, Any] = Field(
        default_factory=dict,
        description="Mapa de capacidades habilitadas para el conector.",
    )
    setup_instructions: list[str] = Field(
        default_factory=list,
        description="Pasos recomendados para habilitar la integración.",
    )


class IntegrationRotateSecretResponse(BaseModel):
    """Respuesta emitida tras rotar el token de una integración."""

    slug: str = Field(
        ...,
        min_length=3,
        max_length=60,
        description="Identificador del conector actualizado.",
    )
    token: str = Field(
        ...,
        min_length=16,
        max_length=200,
        description="Token API recién emitido en formato URL-safe.",
    )
    credential: IntegrationCredentialInfo

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "slug": "erp_sync",
                "token": "4sV2k1lM...",
                "credential": {
                    "token_hint": "LmN7",
                    "rotated_at": "2025-11-06T05:32:00+00:00",
                    "expires_at": "2026-02-04T05:32:00+00:00",
                },
            }
        }
    )


class IntegrationHealthUpdateRequest(BaseModel):
    """Carga útil enviada por los monitores corporativos."""

    status: str = Field(
        ...,
        min_length=2,
        max_length=40,
        description="Estado reportado (operational, degraded, offline, etc.).",
    )
    message: str | None = Field(
        default=None,
        max_length=200,
        description="Descripción breve del resultado del monitoreo.",
    )


class IntegrationWebhookEvent(BaseModel):
    id: int
    event: str
    entity: str
    entity_id: str
    operation: str
    payload: dict[str, Any]
    version: int
    status: SyncOutboxStatus
    attempt_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("payload", mode="before")
    @classmethod
    def _parse_payload(cls, value: Any) -> dict[str, Any]:
        if isinstance(value, str):
            try:
                import json

                return json.loads(value)
            except Exception:  # pragma: no cover - fallback a payload vacío
                return {}
        if isinstance(value, dict):
            return value
        return {}


class IntegrationWebhookAckRequest(BaseModel):
    status: Literal["sent", "failed"]
    error_message: str | None = Field(default=None, max_length=250)


class IntegrationWebhookAckResponse(BaseModel):
    id: int
    status: SyncOutboxStatus
    attempts: int
    error_message: str | None
