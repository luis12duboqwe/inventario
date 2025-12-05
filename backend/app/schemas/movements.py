from __future__ import annotations
from decimal import Decimal
from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
    model_serializer,
)

from ..models import MovementType
from .audit import AuditTrailInfo


class MovementBase(BaseModel):
    """Base para registrar movimientos de inventario (entradas/salidas/ajustes).

    Acepta aliases comunes (device_id, quantity, comment, source_store_id, store_id)
    y los normaliza a las claves en español usadas en nuestra API pública.
    """

    producto_id: int = Field(..., ge=1)
    tipo_movimiento: MovementType
    cantidad: int = Field(..., ge=0)
    comentario: str = Field(..., min_length=5, max_length=255)
    sucursal_origen_id: int | None = Field(default=None, ge=1)
    sucursal_destino_id: int | None = Field(default=None, ge=1)
    almacen_origen_id: int | None = Field(default=None, ge=1)
    almacen_destino_id: int | None = Field(default=None, ge=1)
    unit_cost: Decimal | None = Field(default=None, ge=Decimal("0"))

    @model_validator(mode="before")
    @classmethod
    def _coerce_movement_input(cls, data: Any) -> Any:  # pragma: no cover
        if not isinstance(data, dict):
            return data
        mapping = {
            "producto_id": ["device_id"],
            "tipo_movimiento": ["movement_type"],
            "cantidad": ["quantity"],
            "comentario": ["comment"],
            "sucursal_origen_id": ["tienda_origen_id", "source_store_id"],
            "sucursal_destino_id": ["tienda_destino_id", "branch_id", "store_id"],
            "almacen_origen_id": ["source_warehouse_id"],
            "almacen_destino_id": ["warehouse_id", "destination_warehouse_id"],
        }
        for target, sources in mapping.items():
            if target not in data:
                for s in sources:
                    if s in data:
                        data[target] = data[s]
                        break
        return data

    @field_validator("comentario", mode="before")
    @classmethod
    def _normalize_comment(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("El comentario es obligatorio.")
        normalized = value.strip()
        if len(normalized) < 5:
            raise ValueError("El comentario debe tener al menos 5 caracteres.")
        return normalized

    @model_validator(mode="after")
    def _validate_quantity(self) -> "MovementBase":
        if self.tipo_movimiento in {MovementType.IN, MovementType.OUT} and self.cantidad <= 0:
            raise ValueError(
                "La cantidad debe ser mayor que cero para entradas o salidas.")
        if self.tipo_movimiento == MovementType.ADJUST and self.cantidad < 0:
            raise ValueError("La cantidad no puede ser negativa en un ajuste.")
        return self


class MovementCreate(MovementBase):
    """Carga de datos para registrar movimientos de inventario."""


class MovementResponse(BaseModel):
    """Respuesta de movimiento de inventario con claves en español.

    Se usan nombres internos iguales al modelo (`device_id`, `movement_type`,
    `quantity`, `comment`, `source_store_id`, `store_id`, `performed_by_id`,
    `created_at`) y se serializan a los nombres históricos en español utilizados
    por las pruebas y el frontend (`producto_id`, `tipo_movimiento`, `cantidad`,
    `comentario`, `sucursal_origen_id`, `sucursal_destino_id`, `usuario_id`,
    `fecha`). Esto evita depender de *validation_alias* y reduce warnings.
    """

    id: int
    device_id: int
    movement_type: MovementType
    quantity: int
    comment: str | None = None
    source_store_id: int | None = None
    store_id: int | None = None  # destino
    source_warehouse_id: int | None = None
    warehouse_id: int | None = None
    performed_by_id: int | None = None
    created_at: datetime
    unit_cost: Decimal | None = None
    store_inventory_value: Decimal
    # Propiedades calculadas disponibles en el modelo (usuario, sucursal_origen, sucursal_destino)
    usuario: str | None = None
    sucursal_origen: str | None = None
    sucursal_destino: str | None = None
    almacen_origen: str | None = None
    almacen_destino: str | None = None
    referencia_tipo: str | None = None
    referencia_id: str | None = None
    ultima_accion: AuditTrailInfo | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("unit_cost")
    @classmethod
    def _serialize_unit_cost(cls, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)

    @field_serializer("store_inventory_value")
    @classmethod
    def _serialize_inventory_total(cls, value: Decimal) -> float:
        return float(value)

    @model_serializer
    def _serialize(self) -> dict[str, Any]:  # pragma: no cover - mapeo directo
        return {
            "id": self.id,
            "producto_id": self.device_id,
            "tipo_movimiento": self.movement_type,
            "cantidad": self.quantity,
            "comentario": self.comment,
            "sucursal_origen_id": self.source_store_id,
            "sucursal_origen": self.sucursal_origen,
            "sucursal_destino_id": self.store_id,
            "sucursal_destino": self.sucursal_destino,
            "almacen_origen_id": self.source_warehouse_id,
            "almacen_origen": self.almacen_origen,
            "almacen_destino_id": self.warehouse_id,
            "almacen_destino": self.almacen_destino,
            "usuario_id": self.performed_by_id,
            "usuario": self.usuario,
            "referencia_tipo": self.referencia_tipo,
            "referencia_id": self.referencia_id,
            "fecha": self.created_at,
            "unit_cost": self._serialize_unit_cost(self.unit_cost),
            "store_inventory_value": self._serialize_inventory_total(self.store_inventory_value),
            "ultima_accion": self.ultima_accion,
        }
