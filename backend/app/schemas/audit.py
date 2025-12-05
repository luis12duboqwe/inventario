from __future__ import annotations
import enum
from datetime import datetime, timezone
from typing import Any, Literal, Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    AliasChoices,
    model_validator,
    computed_field,
    field_serializer,
    field_validator,
)

from ..utils import audit as audit_utils


class AuditTrailInfo(BaseModel):
    accion: str
    descripcion: str | None = None
    entidad: str
    registro_id: str
    usuario_id: int | None = None
    usuario: str | None = None
    timestamp: datetime
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class AuditLogResponse(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: str
    details: str | None
    performed_by_id: int | None
    created_at: datetime
    severity: Literal["info", "warning", "critical"] = Field(default="info")
    severity_label: str = Field(default="Informativa")
    module: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices("module", "modulo"),
            serialization_alias="modulo",
        ),
    ]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @model_validator(mode="after")
    def _derive_severity(self) -> "AuditLogResponse":
        severity = audit_utils.classify_severity(
            self.action or "", self.details)
        label = audit_utils.severity_label(severity)
        object.__setattr__(self, "severity", severity)
        object.__setattr__(self, "severity_label", label)
        return self

    @computed_field(alias="accion")
    def accion(self) -> str:
        return self.action


class AuditHighlight(BaseModel):
    id: int
    action: str
    created_at: datetime
    severity: Literal["info", "warning", "critical"]
    entity_type: str
    entity_id: str
    status: Literal["pending", "acknowledged"] = Field(default="pending")
    acknowledged_at: datetime | None = None
    acknowledged_by_id: int | None = None
    acknowledged_by_name: str | None = None
    acknowledged_note: str | None = None

    @field_serializer("created_at")
    @classmethod
    def _serialize_created_at(cls, value: datetime) -> str:
        return value.isoformat()


class AuditAcknowledgedEntity(BaseModel):
    entity_type: str
    entity_id: str
    acknowledged_at: datetime
    acknowledged_by_id: int | None = None
    acknowledged_by_name: str | None = None
    note: str | None = None

    @field_serializer("acknowledged_at")
    @classmethod
    def _serialize_ack_time(cls, value: datetime) -> str:
        return value.isoformat()


class DashboardAuditAlerts(BaseModel):
    total: int
    critical: int
    warning: int
    info: int
    pending_count: int = Field(default=0, ge=0)
    acknowledged_count: int = Field(default=0, ge=0)
    highlights: list[AuditHighlight] = Field(default_factory=list)
    acknowledged_entities: list[AuditAcknowledgedEntity] = Field(
        default_factory=list)

    @computed_field(return_type=bool)  # type: ignore[misc]
    def has_alerts(self) -> bool:
        return self.critical > 0 or self.warning > 0


class AuditUIExportFormat(str, enum.Enum):
    """Formatos válidos para exportar la bitácora de UI."""

    CSV = "csv"
    JSON = "json"


class AuditUIBulkItem(BaseModel):
    ts: datetime = Field(...,
                         description="Marca de tiempo del evento en formato ISO 8601")
    user_id: str | None = Field(
        default=None,
        max_length=120,
        validation_alias=AliasChoices("userId", "user_id"),
        description="Identificador del usuario que generó la acción",
    )
    module: str = Field(..., max_length=80,
                        description="Módulo de la interfaz donde ocurrió")
    action: str = Field(..., max_length=120,
                        description="Acción específica realizada")
    entity_id: str | None = Field(
        default=None,
        max_length=120,
        validation_alias=AliasChoices("entityId", "entity_id"),
        description="Identificador de la entidad relacionada",
    )
    meta: dict[str, Any] | None = Field(
        default=None,
        description="Metadatos adicionales serializados como JSON",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("ts", mode="before")
    @classmethod
    def _coerce_timestamp(cls, value: Any) -> Any:
        # // [PACK32-33-BE] Acepta números en ms o segundos para compatibilidad con la cola local.
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value
        if isinstance(value, (int, float)):
            numeric = float(value)
            if numeric > 10**12:
                numeric /= 1000.0
            return datetime.fromtimestamp(numeric, tz=timezone.utc)
        if isinstance(value, str):
            try:
                numeric = float(value)
            except ValueError:
                return value
            if numeric > 10**12:
                numeric /= 1000.0
            return datetime.fromtimestamp(numeric, tz=timezone.utc)
        return value


class AuditUIBulkRequest(BaseModel):
    items: list[AuditUIBulkItem] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Eventos a persistir en la bitácora",
    )


class AuditUIBulkResponse(BaseModel):
    inserted: int = Field(..., ge=0,
                          description="Cantidad de registros insertados")


class AuditUIRecord(BaseModel):
    id: int
    ts: datetime
    user_id: str | None = None
    module: str
    action: str
    entity_id: str | None = None
    meta: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("ts")
    @classmethod
    def _serialize_ts(cls, value: datetime) -> str:
        return value.isoformat()


class AuditUIListResponse(BaseModel):
    items: list[AuditUIRecord] = Field(default_factory=list)
    total: int = Field(..., ge=0)
    limit: int = Field(..., ge=1)
    offset: int = Field(..., ge=0)
    has_more: bool = Field(default=False)
