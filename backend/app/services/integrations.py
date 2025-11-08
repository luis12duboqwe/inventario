"""Gestión interna de conectores externos."""

from __future__ import annotations

import copy
import hashlib
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass(slots=True)
class IntegrationHealthState:
    """Estado operativo reportado para un conector externo."""

    status: str = "desconocido"
    checked_at: datetime | None = None
    message: str | None = None


@dataclass(slots=True)
class IntegrationCredentialState:
    """Información sensible asociada al token API de la integración."""

    token_hash: str
    token_hint: str
    rotated_at: datetime
    expires_at: datetime


@dataclass(slots=True)
class IntegrationRecord:
    """Metadatos consolidados de un conector corporativo."""

    slug: str
    name: str
    category: str
    description: str
    documentation_url: str | None
    auth_type: str
    status: str
    events: list[str] = field(default_factory=list)
    features: dict[str, Any] = field(default_factory=dict)
    setup_instructions: list[str] = field(default_factory=list)
    supports_push: bool = True
    supports_pull: bool = False
    health: IntegrationHealthState = field(default_factory=IntegrationHealthState)
    credential: IntegrationCredentialState | None = None


class IntegrationNotFoundError(LookupError):
    """Señala que la integración solicitada no existe en el registro."""


class IntegrationRegistry:
    """Registro en memoria de integraciones externas certificadas."""

    DEFAULT_TOKEN_TTL_DAYS = 90

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._providers: dict[str, IntegrationRecord] = {}
        self._bootstrap_defaults()

    def _bootstrap_defaults(self) -> None:
        """Carga los conectores homologados con valores iniciales."""

        now = datetime.now(timezone.utc)
        self._providers = {
            "zapier": self._build_record(
                slug="zapier",
                name="Zapier Inventory Bridge",
                category="automatizacion",
                description=(
                    "Sincroniza inventario, ventas y cartera de clientes con flujos"
                    " Zapier.")
                ,
                documentation_url="https://docs.softmobile.mx/integraciones/zapier",
                auth_type="api_key",
                status="active",
                events=[
                    "inventory.device.updated",
                    "sales.order.completed",
                    "customers.balance.changed",
                ],
                features={
                    "webhooks": True,
                    "bulk_export": False,
                    "retry_strategy": "exponencial",
                },
                setup_instructions=[
                    "Crear flujo Zapier con el hook corporativo proporcionado.",
                    "Configurar cabecera X-Reason con motivo corporativo.",
                    "Mapear campos obligatorios (sku, quantity, unit_price).",
                ],
                supports_push=True,
                supports_pull=True,
                now=now,
            ),
            "power_bi": self._build_record(
                slug="power_bi",
                name="Power BI Streaming",
                category="analitica",
                description=(
                    "Publica métricas de inventario y ventas en datasets en"
                    " streaming de Power BI."),
                documentation_url="https://docs.softmobile.mx/integraciones/power-bi",
                auth_type="api_key",
                status="active",
                events=[
                    "inventory.snapshot.generated",
                    "sales.daily_summary",
                ],
                features={
                    "webhooks": False,
                    "bulk_export": True,
                    "push_dataset_refresh": True,
                },
                setup_instructions=[
                    "Registrar dataset streaming en Power BI.",
                    "Configurar URL de ingestión en el panel de integraciones.",
                    "Programar refrescos cada hora desde el monitor corporativo.",
                ],
                supports_push=False,
                supports_pull=True,
                now=now,
            ),
            "erp_sync": self._build_record(
                slug="erp_sync",
                name="ERP Sync Gateway",
                category="erp",
                description=(
                    "Canal bidireccional para sincronizar stock, órdenes de compra"
                    " y facturación con el ERP contable."),
                documentation_url="https://docs.softmobile.mx/integraciones/erp",
                auth_type="api_key",
                status="beta",
                events=[
                    "inventory.transfer.completed",
                    "purchases.order.received",
                    "sales.invoice.issued",
                ],
                features={
                    "webhooks": True,
                    "bulk_export": True,
                    "conflict_resolution": "last-write-wins",
                },
                setup_instructions=[
                    "Registrar endpoints ERP para recepciones y devoluciones.",
                    "Configurar colas híbridas con prioridad HIGH.",
                    "Habilitar reconciliación nocturna mediante cron.",
                ],
                supports_push=True,
                supports_pull=True,
                now=now,
            ),
        }

    def _build_record(
        self,
        *,
        slug: str,
        name: str,
        category: str,
        description: str,
        documentation_url: str | None,
        auth_type: str,
        status: str,
        events: list[str],
        features: dict[str, Any],
        setup_instructions: list[str],
        supports_push: bool,
        supports_pull: bool,
        now: datetime,
    ) -> IntegrationRecord:
        token = self._generate_token()
        credential = self._build_credential(token, now)
        return IntegrationRecord(
            slug=slug,
            name=name,
            category=category,
            description=description,
            documentation_url=documentation_url,
            auth_type=auth_type,
            status=status,
            events=list(events),
            features=dict(features),
            setup_instructions=list(setup_instructions),
            supports_push=supports_push,
            supports_pull=supports_pull,
            credential=credential,
            health=IntegrationHealthState(status="operational", checked_at=now),
        )

    def _generate_token(self) -> str:
        return secrets.token_urlsafe(48)

    def _build_credential(self, token: str, now: datetime) -> IntegrationCredentialState:
        expires_at = now + timedelta(days=self.DEFAULT_TOKEN_TTL_DAYS)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        hint = token[-4:]
        return IntegrationCredentialState(
            token_hash=token_hash,
            token_hint=hint,
            rotated_at=now,
            expires_at=expires_at,
        )

    def list_providers(self) -> list[IntegrationRecord]:
        """Entrega copias independientes de los conectores registrados."""

        with self._lock:
            return [copy.deepcopy(record) for record in self._providers.values()]

    def get_provider(self, slug: str) -> IntegrationRecord:
        """Obtiene un conector específico o lanza error si no existe."""

        with self._lock:
            record = self._providers.get(slug)
            if record is None:
                raise IntegrationNotFoundError(slug)
            return copy.deepcopy(record)

    def rotate_token(self, slug: str) -> tuple[IntegrationRecord, str]:
        """Genera un nuevo token seguro y actualiza su hash almacenado."""

        with self._lock:
            record = self._providers.get(slug)
            if record is None:
                raise IntegrationNotFoundError(slug)
            new_token = self._generate_token()
            now = datetime.now(timezone.utc)
            record.credential = self._build_credential(new_token, now)
            self._providers[slug] = record
            return copy.deepcopy(record), new_token

    def update_health(self, slug: str, status: str, message: str | None) -> IntegrationRecord:
        """Actualiza el estado de salud reportado para la integración."""

        with self._lock:
            record = self._providers.get(slug)
            if record is None:
                raise IntegrationNotFoundError(slug)
            record.health = IntegrationHealthState(
                status=status,
                checked_at=datetime.now(timezone.utc),
                message=message,
            )
            self._providers[slug] = record
            return copy.deepcopy(record)


integration_registry = IntegrationRegistry()

__all__ = [
    "IntegrationRegistry",
    "IntegrationRecord",
    "IntegrationCredentialState",
    "IntegrationHealthState",
    "IntegrationNotFoundError",
    "integration_registry",
]
