from __future__ import annotations
from datetime import datetime
from typing import Annotated

from pydantic import (
    BaseModel,
    Field,
    AliasChoices,
    ConfigDict,
    field_serializer,
)

from ..models import SystemLogLevel


class SystemLogEntry(BaseModel):
    id_log: Annotated[int, Field(
        validation_alias=AliasChoices("id_log", "id"))]
    usuario: str | None
    modulo: str
    accion: str
    descripcion: str
    fecha: datetime
    nivel: SystemLogLevel
    ip_origen: str | None = None
    audit_log_id: Annotated[
        int | None,
        Field(
            default=None,
            validation_alias=AliasChoices("audit_log_id"),
            serialization_alias="audit_log_id",
        ),
    ]

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("fecha", when_used="json")
    @classmethod
    def _serialize_fecha(cls, value: datetime) -> str:
        return value.isoformat()


class SystemErrorEntry(BaseModel):
    id_error: Annotated[
        int,
        Field(validation_alias=AliasChoices("id_error", "id")),
    ]
    mensaje: str
    stack_trace: str | None
    modulo: str
    fecha: datetime
    usuario: str | None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("fecha", when_used="json")
    @classmethod
    def _serialize_fecha(cls, value: datetime) -> str:
        return value.isoformat()
