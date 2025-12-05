from __future__ import annotations
from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
    model_serializer,
)

from .movements import MovementResponse


class WarehouseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    code: str = Field(..., min_length=1, max_length=30)
    is_default: bool = Field(default=False)

    @model_validator(mode="before")
    @classmethod
    def _normalize_aliases(cls, data: Any) -> Any:  # pragma: no cover - mapeo directo
        if not isinstance(data, dict):
            return data
        alias_map = {"name": ["nombre"], "code": ["codigo"]}
        for target, sources in alias_map.items():
            if target not in data:
                for source in sources:
                    if source in data:
                        data[target] = data[source]
                        break
        return data

    @field_validator("name", "code", mode="before")
    @classmethod
    def _strip_values(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("valor_requerido")
        normalized = value.strip()
        if not normalized:
            raise ValueError("valor_requerido")
        return normalized


class WarehouseCreate(WarehouseBase):
    """Carga para registrar un nuevo almacén ligado a una sucursal."""


class WarehouseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(default=None, min_length=1, max_length=30)
    is_default: bool | None = None


class WarehouseResponse(BaseModel):
    id: int
    store_id: int
    name: str
    code: str
    is_default: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WarehouseTransferCreate(BaseModel):
    store_id: int = Field(..., ge=1)
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)
    source_warehouse_id: int = Field(..., ge=1)
    destination_warehouse_id: int = Field(..., ge=1)
    reason: str = Field(..., min_length=5, max_length=255)

    @field_validator("reason")
    @classmethod
    def _normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 5:
            raise ValueError("El motivo debe tener al menos 5 caracteres.")
        return normalized


class WarehouseTransferResponse(BaseModel):
    movement_out: MovementResponse
    movement_in: MovementResponse


class WMSBinBase(BaseModel):
    codigo: str = Field(
        ..., min_length=1, max_length=60, description="Código único del bin dentro de la sucursal"
    )
    pasillo: str | None = Field(default=None, max_length=60)
    rack: str | None = Field(default=None, max_length=60)
    nivel: str | None = Field(default=None, max_length=60)
    descripcion: str | None = Field(default=None, max_length=255)

    @model_validator(mode="before")
    @classmethod
    def _coerce_bin_aliases(cls, data: Any) -> Any:  # pragma: no cover - simple mapeo
        if not isinstance(data, dict):
            return data
        alias_map = {
            "codigo": ["code"],
            "pasillo": ["aisle"],
            "nivel": ["level"],
            "descripcion": ["description"],
        }
        for target, sources in alias_map.items():
            if target not in data:
                for source in sources:
                    if source in data:
                        data[target] = data[source]
                        break
        return data

    @field_validator("codigo", mode="before")
    @classmethod
    def _normalize_code(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("codigo_requerido")
        normalized = value.strip()
        if not normalized:
            raise ValueError("codigo_requerido")
        return normalized


class WMSBinCreate(WMSBinBase):
    """Carga de datos necesaria para registrar un bin."""


class WMSBinUpdate(BaseModel):
    codigo: str | None = Field(default=None, max_length=60)
    pasillo: str | None = Field(default=None, max_length=60)
    rack: str | None = Field(default=None, max_length=60)
    nivel: str | None = Field(default=None, max_length=60)
    descripcion: str | None = Field(default=None, max_length=255)


class WMSBinResponse(BaseModel):
    """Respuesta de un bin WMS con claves en español.

    Internamente usamos los nombres de atributos reales del modelo SQLAlchemy
    (code, store_id, created_at, updated_at) y los convertimos a las claves
    originales en español mediante un serializer personalizado para no depender
    de *validation_alias*/"serialization_alias" que generan warnings en Pydantic v2.
    """

    id: int
    code: str
    store_id: int
    aisle: str | None = None
    rack: str | None = None
    level: str | None = None
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_serializer
    def _serialize(self) -> dict[str, Any]:  # pragma: no cover - mapeo directo
        return {
            "id": self.id,
            "codigo": self.code,
            "sucursal_id": self.store_id,
            "pasillo": self.aisle,
            "rack": self.rack,
            "nivel": self.level,
            "descripcion": self.description,
            "fecha_creacion": self.created_at,
            "fecha_actualizacion": self.updated_at,
        }


class DeviceBinAssignmentResponse(BaseModel):
    producto_id: int = Field(..., ge=1)
    bin: WMSBinResponse
    asignado_en: datetime
    desasignado_en: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
