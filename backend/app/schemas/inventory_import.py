from __future__ import annotations
from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class SmartImportColumnMatch(BaseModel):
    campo: str
    encabezado_origen: str | None = None
    estado: Literal["ok", "pendiente", "falta"]
    tipo_dato: str | None = None
    ejemplos: list[str] = Field(default_factory=list)


class InventorySmartImportPreview(BaseModel):
    columnas: list[SmartImportColumnMatch]
    columnas_detectadas: dict[str, str | None]
    columnas_faltantes: list[str] = Field(default_factory=list)
    total_filas: int
    registros_incompletos_estimados: int
    advertencias: list[str] = Field(default_factory=list)
    patrones_sugeridos: dict[str, str] = Field(default_factory=dict)


class ImportValidationSummary(BaseModel):
    registros_revisados: int
    advertencias: int
    errores: int
    campos_faltantes: list[str] = Field(default_factory=list)
    tiempo_total: float | None = None


class InventorySmartImportResult(BaseModel):
    total_procesados: int
    nuevos: int
    actualizados: int
    registros_incompletos: int
    columnas_faltantes: list[str] = Field(default_factory=list)
    advertencias: list[str] = Field(default_factory=list)
    tiendas_nuevas: list[str] = Field(default_factory=list)
    duracion_segundos: float | None = None
    resumen: str
    validacion_resumen: ImportValidationSummary | None = None


class InventorySmartImportResponse(BaseModel):
    preview: InventorySmartImportPreview
    resultado: InventorySmartImportResult | None = None


class InventoryImportError(BaseModel):
    row: int = Field(
        ..., ge=1, description="Número de fila del archivo que provocó la incidencia."
    )
    message: str = Field(
        ..., min_length=1, description="Código interno o descripción del error detectado."
    )


class InventoryImportSummary(BaseModel):
    created: int = Field(
        ..., ge=0, description="Cantidad de productos creados durante la importación."
    )
    updated: int = Field(
        ..., ge=0, description="Cantidad de productos actualizados durante la importación."
    )
    skipped: int = Field(
        ..., ge=0, description="Registros omitidos por datos insuficientes o inconsistencias."
    )
    errors: list[InventoryImportError] = Field(
        default_factory=list,
        description="Listado de errores asociados a filas específicas del archivo.",
    )


class ImportValidationBase(BaseModel):
    tipo: str
    severidad: str
    descripcion: str
    fecha: datetime
    corregido: bool


class ImportValidation(ImportValidationBase):
    id: int
    producto_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ImportValidationDevice(BaseModel):
    id: int
    store_id: int
    store_name: str
    sku: str
    name: str
    imei: str | None = None
    serial: str | None = None
    marca: str | None = None
    modelo: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ImportValidationDetail(ImportValidation):
    device: ImportValidationDevice | None = None


class InventoryImportHistoryEntry(BaseModel):
    id: int
    nombre_archivo: str
    fecha: datetime
    columnas_detectadas: dict[str, str | None]
    registros_incompletos: int
    total_registros: int
    nuevos: int
    actualizados: int
    advertencias: list[str]
    duracion_segundos: float | None = None

    model_config = ConfigDict(from_attributes=True)
