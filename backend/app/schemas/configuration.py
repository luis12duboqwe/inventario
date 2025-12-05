from __future__ import annotations
import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class ConfigurationParameterType(str, enum.Enum):
    """Tipos permitidos para los parámetros configurables."""

    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    JSON = "json"


class ConfigurationRateBase(BaseModel):
    slug: str = Field(..., min_length=1, max_length=80)
    name: str = Field(..., min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    value: Decimal = Field(..., description="Valor numérico de la tasa")
    unit: str = Field(..., min_length=1, max_length=40)
    currency: str | None = Field(default=None, max_length=10)
    effective_from: date | None = Field(default=None)
    effective_to: date | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("slug", "name", "unit", mode="before")
    @classmethod
    def _strip_required(cls, value: Any) -> str:
        if value is None:
            raise ValueError("El valor es obligatorio")
        text = str(value).strip()
        if not text:
            raise ValueError("El valor es obligatorio")
        return text

    @field_validator("currency", "description", mode="before")
    @classmethod
    def _strip_optional(cls, value: Any | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class ConfigurationRateCreate(ConfigurationRateBase):
    """Carga útil para registrar una tasa de configuración."""


class ConfigurationRateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    value: Decimal | None = Field(default=None)
    unit: str | None = Field(default=None, min_length=1, max_length=40)
    currency: str | None = Field(default=None, max_length=10)
    effective_from: date | None = Field(default=None)
    effective_to: date | None = Field(default=None)
    metadata: dict[str, Any] | None = None
    is_active: bool | None = None

    @field_validator("name", "unit", mode="before")
    @classmethod
    def _strip_update_required(cls, value: Any | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("currency", "description", mode="before")
    @classmethod
    def _strip_update_optional(cls, value: Any | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class ConfigurationRateResponse(ConfigurationRateBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer("value")
    @classmethod
    def _serialize_value(cls, value: Decimal) -> str:
        return format(value, "f")


class ConfigurationParameterBase(BaseModel):
    key: str = Field(..., min_length=1, max_length=120)
    name: str = Field(..., min_length=1, max_length=120)
    category: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("key", "name", mode="before")
    @classmethod
    def _strip_required(cls, value: Any) -> str:
        if value is None:
            raise ValueError("El valor es obligatorio")
        text = str(value).strip()
        if not text:
            raise ValueError("El valor es obligatorio")
        return text

    @field_validator("category", "description", mode="before")
    @classmethod
    def _strip_optional(cls, value: Any | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class ConfigurationParameterCreate(ConfigurationParameterBase):
    value_type: ConfigurationParameterType = Field(
        default=ConfigurationParameterType.STRING)
    value: Any = Field(...)
    is_sensitive: bool = Field(default=False)


class ConfigurationParameterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    value_type: ConfigurationParameterType | None = None
    value: Any | None = None
    is_sensitive: bool | None = None
    metadata: dict[str, Any] | None = None
    is_active: bool | None = None

    @field_validator("name", "category", mode="before")
    @classmethod
    def _strip_optional(cls, value: Any | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("description", mode="before")
    @classmethod
    def _strip_description(cls, value: Any | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class ConfigurationParameterResponse(ConfigurationParameterBase):
    id: int
    value_type: ConfigurationParameterType
    value: Any
    is_sensitive: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConfigurationXmlTemplateCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=80)
    version: str = Field(..., min_length=1, max_length=40)
    description: str | None = Field(default=None, max_length=255)
    namespace: str | None = Field(default=None, max_length=255)
    schema_location: str | None = Field(default=None, max_length=255)
    content: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("code", "version", mode="before")
    @classmethod
    def _strip_required(cls, value: Any) -> str:
        if value is None:
            raise ValueError("El valor es obligatorio")
        text = str(value).strip()
        if not text:
            raise ValueError("El valor es obligatorio")
        return text

    @field_validator("description", "namespace", "schema_location", mode="before")
    @classmethod
    def _strip_optional(cls, value: Any | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class ConfigurationXmlTemplateUpdate(BaseModel):
    version: str | None = Field(default=None, min_length=1, max_length=40)
    description: str | None = Field(default=None, max_length=255)
    namespace: str | None = Field(default=None, max_length=255)
    schema_location: str | None = Field(default=None, max_length=255)
    content: str | None = Field(default=None, min_length=1)
    metadata: dict[str, Any] | None = None
    is_active: bool | None = None

    @field_validator("version", "description", "namespace", "schema_location", mode="before")
    @classmethod
    def _strip_optional(cls, value: Any | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class ConfigurationXmlTemplateResponse(BaseModel):
    id: int
    code: str
    version: str
    description: str | None
    namespace: str | None
    schema_location: str | None
    content: str
    checksum: str
    metadata: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConfigurationOverview(BaseModel):
    rates: list[ConfigurationRateResponse]
    xml_templates: list[ConfigurationXmlTemplateResponse]
    parameters: list[ConfigurationParameterResponse]

    model_config = ConfigDict(from_attributes=True)


class ConfigurationSyncResult(BaseModel):
    rates_activated: int = Field(default=0, ge=0)
    rates_deactivated: int = Field(default=0, ge=0)
    templates_activated: int = Field(default=0, ge=0)
    templates_deactivated: int = Field(default=0, ge=0)
    parameters_activated: int = Field(default=0, ge=0)
    parameters_deactivated: int = Field(default=0, ge=0)
    processed_files: list[str] = Field(default_factory=list)
