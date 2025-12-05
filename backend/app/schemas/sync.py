from __future__ import annotations
import enum
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

from ..models import SyncMode, SyncStatus, SyncOutboxStatus, SyncOutboxPriority, SyncQueueStatus
from .common import ensure_aware


class SyncSessionResponse(BaseModel):
    id: int
    store_id: int | None
    mode: SyncMode
    status: SyncStatus
    started_at: datetime
    finished_at: datetime | None
    triggered_by_id: int | None
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)


class SyncRequest(BaseModel):
    store_id: int | None = Field(default=None, ge=1)


class SyncOutboxEntryResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    operation: str
    payload: dict[str, Any]
    attempt_count: int
    last_attempt_at: datetime | None
    status: SyncOutboxStatus
    priority: SyncOutboxPriority
    error_message: str | None
    conflict_flag: bool
    version: int
    created_at: datetime
    updated_at: datetime
    latency_ms: int | None = Field(
        default=None,
        description="Milisegundos transcurridos desde la creación del evento hasta ahora.",
    )
    processing_latency_ms: int | None = Field(
        default=None,
        description="Milisegundos transcurridos entre la creación y el último intento.",
    )
    status_detail: str | None = Field(
        default=None,
        description="Estado detallado normalizado para la interfaz (pendiente/en_progreso/error/completado).",
    )

    model_config = ConfigDict(from_attributes=True)

    @field_validator("payload", mode="before")
    @classmethod
    def _parse_payload(cls, value: Any) -> dict[str, Any]:
        if isinstance(value, str):
            try:
                import json

                return json.loads(value)
            except Exception:  # pragma: no cover - fallback to empty payload
                return {}
        if isinstance(value, dict):
            return value
        return {}

    @model_validator(mode="after")
    def _compute_latencies(self) -> "SyncOutboxEntryResponse":  # pragma: no cover - cálculo derivado
        now = datetime.now(timezone.utc)
        created_at = ensure_aware(self.created_at)
        last_attempt = ensure_aware(self.last_attempt_at or self.updated_at)

        latency: int | None = None
        processing_latency: int | None = None

        if created_at:
            latency = int((now - created_at).total_seconds() * 1000)
        if created_at and last_attempt:
            processing_latency = int(
                (last_attempt - created_at).total_seconds() * 1000)

        detail = "pendiente"
        if self.status == SyncOutboxStatus.FAILED:
            detail = "error"
        elif self.status == SyncOutboxStatus.SENT:
            detail = "completado"
        else:
            # Consideramos "en progreso" si la marca de actualización es reciente.
            recent_threshold_ms = 90_000
            if latency is not None and last_attempt:
                delta_ms = int((now - last_attempt).total_seconds() * 1000)
                if delta_ms <= recent_threshold_ms:
                    detail = "en_progreso"

        object.__setattr__(self, "latency_ms", latency)
        object.__setattr__(self, "processing_latency_ms", processing_latency)
        object.__setattr__(self, "status_detail", detail)
        return self


class SyncOutboxStatsEntry(BaseModel):
    entity_type: str
    priority: SyncOutboxPriority
    total: int
    pending: int
    failed: int
    conflicts: int
    latest_update: datetime | None
    oldest_pending: datetime | None
    last_conflict_at: datetime | None


# // [PACK35-backend]
class SyncQueueProgressSummary(BaseModel):
    percent: float
    total: int
    processed: int
    pending: int
    failed: int
    last_updated: datetime | None
    oldest_pending: datetime | None


# // [PACK35-backend]
class SyncHybridComponentSummary(BaseModel):
    total: int
    processed: int
    pending: int
    failed: int
    latest_update: datetime | None
    oldest_pending: datetime | None


# // [PACK35-backend]
class SyncHybridProgressComponents(BaseModel):
    queue: SyncHybridComponentSummary
    outbox: SyncHybridComponentSummary


# // [PACK35-backend]
class SyncHybridProgressSummary(BaseModel):
    percent: float
    total: int
    processed: int
    pending: int
    failed: int
    components: SyncHybridProgressComponents


# // [PACK35-backend]
class SyncHybridForecast(BaseModel):
    lookback_minutes: int
    processed_recent: int
    processed_queue: int
    processed_outbox: int
    attempts_total: int
    attempts_successful: int
    success_rate: float
    events_per_minute: float
    backlog_pending: int
    backlog_failed: int
    backlog_total: int
    estimated_minutes_remaining: float | None
    estimated_completion: datetime | None
    generated_at: datetime
    progress: SyncHybridProgressSummary


# // [PACK35-backend]
class SyncHybridModuleBreakdownComponent(BaseModel):
    total: int
    processed: int
    pending: int
    failed: int


# // [PACK35-backend]
class SyncHybridModuleBreakdownItem(BaseModel):
    module: str
    label: str
    total: int
    processed: int
    pending: int
    failed: int
    percent: float
    queue: SyncHybridModuleBreakdownComponent
    outbox: SyncHybridModuleBreakdownComponent


# // [PACK35-backend]
class SyncHybridRemainingBreakdown(BaseModel):
    total: int
    pending: int
    failed: int
    remote_pending: int
    remote_failed: int
    outbox_pending: int
    outbox_failed: int
    estimated_minutes_remaining: float | None
    estimated_completion: datetime | None


# // [PACK35-backend]
class SyncHybridOverview(BaseModel):
    generated_at: datetime
    percent: float
    total: int
    processed: int
    pending: int
    failed: int
    remaining: SyncHybridRemainingBreakdown
    queue_summary: SyncQueueProgressSummary | None
    progress: SyncHybridProgressSummary
    forecast: SyncHybridForecast
    breakdown: list[SyncHybridModuleBreakdownItem]


# // [PACK35-backend]
class SyncQueueEvent(BaseModel):
    event_type: str = Field(..., min_length=3, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, max_length=120)

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "event_type": "inventory.movement",
            "payload": {"store_id": 1, "device_id": 42, "quantity": -1},
            "idempotency_key": "inventory-movement-42-20250301",
        }
    })


# // [PACK35-backend]
class SyncQueueEntryResponse(BaseModel):
    id: int
    event_type: str
    payload: dict[str, Any]
    idempotency_key: str | None
    status: SyncQueueStatus
    attempts: int
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("payload", mode="before")
    @classmethod
    def _normalize_payload(cls, value: Any) -> dict[str, Any]:
        if isinstance(value, str):
            try:
                import json

                return json.loads(value)
            except Exception:  # pragma: no cover - fallback to empty payload
                return {}
        if isinstance(value, dict):
            return value
        return {}


# // [PACK35-backend]
class SyncQueueAttemptResponse(BaseModel):
    id: int
    queue_id: int
    attempted_at: datetime
    success: bool
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)


# // [PACK35-backend]
class SyncQueueEnqueueRequest(BaseModel):
    events: list[SyncQueueEvent]

    @model_validator(mode="after")
    def _ensure_events(self) -> "SyncQueueEnqueueRequest":
        if not self.events:
            raise ValueError(
                "Debes proporcionar al menos un evento para encolar")
        return self


# // [PACK35-backend]
class SyncQueueEnqueueResponse(BaseModel):
    queued: list[SyncQueueEntryResponse]
    reused: list[SyncQueueEntryResponse] = Field(default_factory=list)


# // [PACK35-backend]
class SyncQueueDispatchResult(BaseModel):
    processed: int
    sent: int
    failed: int
    retried: int


class SyncSessionCompact(BaseModel):
    id: int
    mode: SyncMode
    status: SyncStatus
    started_at: datetime
    finished_at: datetime | None
    error_message: str | None


class SyncStoreHistory(BaseModel):
    store_id: int | None
    store_name: str
    sessions: list[SyncSessionCompact]


class SyncBranchHealth(str, enum.Enum):
    OPERATIVE = "operativa"
    WARNING = "alerta"
    CRITICAL = "critica"
    UNKNOWN = "sin_registros"


class SyncBranchStoreDetail(BaseModel):
    store_id: int
    store_name: str
    quantity: int


class SyncBranchOverview(BaseModel):
    store_id: int
    store_name: str
    store_code: str
    timezone: str
    inventory_value: Decimal
    last_sync_at: datetime | None
    last_sync_mode: SyncMode | None
    last_sync_status: SyncStatus | None
    health: SyncBranchHealth
    health_label: str
    pending_transfers: int
    open_conflicts: int


class SyncConflictLog(BaseModel):
    id: int
    sku: str
    product_name: str | None
    detected_at: datetime
    difference: int
    severity: SyncBranchHealth
    stores_max: list[SyncBranchStoreDetail]
    stores_min: list[SyncBranchStoreDetail]


class SyncConflictReportFilters(BaseModel):
    store_id: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    severity: SyncBranchHealth | None = None


class SyncConflictReportTotals(BaseModel):
    count: int
    critical: int
    warning: int
    affected_skus: int


class SyncConflictReport(BaseModel):
    generated_at: datetime
    filters: SyncConflictReportFilters
    totals: SyncConflictReportTotals
    items: list[SyncConflictLog]


class SyncDiscrepancyReportFilters(BaseModel):
    store_ids: list[int] = Field(default_factory=list)
    date_from: datetime | None = None
    date_to: datetime | None = None
    severity: SyncBranchHealth | None = None
    min_difference: int | None = None


class SyncDiscrepancyReportTotals(BaseModel):
    total_conflicts: int
    warnings: int
    critical: int
    max_difference: int | None
    affected_skus: int


class SyncDiscrepancyReport(BaseModel):
    generated_at: datetime
    filters: SyncDiscrepancyReportFilters
    totals: SyncDiscrepancyReportTotals
    items: list[SyncConflictLog]


class SyncOutboxReplayRequest(BaseModel):
    ids: list[int] = Field(..., min_length=1)


class SyncOutboxPriorityUpdate(BaseModel):
    priority: SyncOutboxPriority
