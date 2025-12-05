"""Esquemas comunes y utilitarios para la API."""
from __future__ import annotations

import enum
import re
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class BackupExportFormat(str, enum.Enum):
    """Formatos disponibles para exportar archivos de respaldo."""

    ZIP = "zip"
    SQL = "sql"
    JSON = "json"


class BinaryFileResponse(BaseModel):
    filename: str = Field(
        ...,
        description="Nombre sugerido del archivo generado.",
    )
    media_type: str = Field(
        ...,
        description="Tipo MIME del recurso entregado como archivo.",
    )
    description: str = Field(
        default="El archivo se entrega como contenido binario en el cuerpo de la respuesta.",
        description="Descripción general del archivo exportado.",
    )

    model_config = ConfigDict(json_schema_extra={"example": {
        "filename": "reporte.pdf",
        "media_type": "application/pdf",
        "description": "El archivo se entrega como contenido binario en el cuerpo de la respuesta.",
    }})

    def content_disposition(self, disposition: str = "attachment") -> dict[str, str]:
        """Construye el encabezado Content-Disposition para descargas."""

        sanitized = self.filename.replace("\n", " ").replace("\r", " ")
        return {"Content-Disposition": f"{disposition}; filename={sanitized}"}


class HTMLDocumentResponse(BaseModel):
    """Describe un documento HTML estático entregado como respuesta."""

    content: str = Field(
        ...,
        description="Contenido HTML completo renderizado por el servicio.",
        min_length=1,
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "content": "<!DOCTYPE html><html lang=\"es\"><head>...</head><body>...</body></html>",
            }
        },
    )


class HealthStatusResponse(BaseModel):
    status: str = Field(
        ...,
        description="Estado operativo general del servicio (por ejemplo: ok, degradado).",
        min_length=2,
        max_length=40,
    )


class RootWelcomeResponse(BaseModel):
    message: str = Field(
        ...,
        description="Mensaje de bienvenida mostrado en la raíz del servicio.",
        min_length=3,
        max_length=120,
    )
    service: str = Field(
        ...,
        description="Nombre visible del servicio o módulo que responde.",
        min_length=3,
        max_length=120,
    )


class LanDatabaseSummary(BaseModel):
    engine: str = Field(
        ..., description="Motor de base de datos detectado", min_length=3, max_length=60
    )
    location: str = Field(
        ..., description="Ruta o identificador de la base de datos", min_length=2, max_length=255
    )
    writable: bool = Field(
        ..., description="Indica si la instancia permite escritura local"
    )
    shared_over_lan: bool = Field(
        ..., description="Confirma que la base puede atender peticiones de otros nodos LAN"
    )


class LanDiscoveryResponse(BaseModel):
    enabled: bool = Field(...,
                          description="Estado de la función de descubrimiento")
    host: str = Field(...,
                      description="Host o IP anunciada en la LAN", min_length=3)
    port: int = Field(
        ...,
        description="Puerto en el que escucha la API",
        ge=1,
        le=65535,
    )
    protocol: str = Field(
        default="http",
        description="Protocolo sugerido para los clientes LAN",
        pattern="^https?$",
    )
    api_base_url: str = Field(
        ...,
        description="URL base construida para que los terminales se conecten",
        min_length=4,
        max_length=255,
    )
    database: LanDatabaseSummary
    notes: list[str] = Field(
        default_factory=list,
        description="Recomendaciones adicionales para el despliegue en LAN",
        max_length=20,
    )


class ContactHistoryEntry(BaseModel):
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    note: str = Field(..., min_length=3, max_length=255)

    @field_validator("note")
    @classmethod
    def _normalize_note(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("La nota debe tener al menos 3 caracteres.")
        return normalized

    @field_serializer("timestamp")
    @classmethod
    def _serialize_timestamp(cls, value: datetime) -> str:
        return value.isoformat()


_RTN_TEMPLATE = "{0}-{1}-{2}"


def normalize_rtn_value(value: str | None) -> str:
    digits = re.sub(r"[^0-9]", "", value or "")
    if len(digits) != 14:
        raise ValueError(
            "El RTN debe contener 14 dígitos (formato ####-####-######).")
    return _RTN_TEMPLATE.format(digits[:4], digits[4:8], digits[8:])


def normalize_optional_rtn_value(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return normalize_rtn_value(cleaned)


def ensure_aware(dt: datetime | None) -> datetime | None:
    """Normaliza fechas naive a UTC para evitar desajustes de zona horaria."""

    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class DashboardChartPoint(BaseModel):
    label: str
    value: float
