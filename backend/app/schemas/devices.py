from __future__ import annotations
from decimal import Decimal
from datetime import date, datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_serializer,
    field_validator,
    model_validator,
)

from ..models import CommercialState


class DeviceIdentifierBase(BaseModel):
    imei_1: str | None = Field(default=None, max_length=18)
    imei_2: str | None = Field(default=None, max_length=18)
    numero_serie: str | None = Field(default=None, max_length=120)
    estado_tecnico: str | None = Field(default=None, max_length=60)
    observaciones: str | None = Field(default=None, max_length=1024)

    @field_validator("imei_1", "imei_2", "numero_serie", mode="before")
    @classmethod
    def _normalize_identifier(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("estado_tecnico", "observaciones", mode="before")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def _validate_identifiers(self) -> "DeviceIdentifierBase":
        identifiers = [self.imei_1, self.imei_2, self.numero_serie]
        if not any(identifiers):
            raise ValueError(
                "Debe registrar al menos un IMEI o número de serie.")
        if self.imei_1 and self.imei_2 and self.imei_1 == self.imei_2:
            raise ValueError("El IMEI 1 y el IMEI 2 no pueden ser idénticos.")
        return self


class DeviceIdentifierRequest(DeviceIdentifierBase):
    """Payload utilizado para registrar identificadores de dispositivos."""


class DeviceIdentifierResponse(DeviceIdentifierBase):
    id: int
    producto_id: int

    model_config = ConfigDict(from_attributes=True)


class DeviceBase(BaseModel):
    sku: str = Field(..., max_length=80,
                     description="Identificador único del producto")
    name: str = Field(..., max_length=120,
                      description="Descripción del dispositivo")
    quantity: int = Field(
        default=0, ge=0, description="Cantidad disponible en inventario")
    warehouse_id: int | None = Field(
        default=None,
        ge=1,
        description="Almacén dentro de la sucursal que resguarda el stock",
    )
    unit_price: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Precio unitario referencial del dispositivo",
    )
    minimum_stock: int = Field(
        default=0,
        ge=0,
        description="Stock mínimo aceptable antes de escalar una alerta",
    )
    reorder_point: int = Field(
        default=0,
        ge=0,
        description="Nivel objetivo para disparar un reabastecimiento",
    )
    precio_venta: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Precio público sugerido del dispositivo",
    )
    imei: str | None = Field(default=None, max_length=18,
                             description="IMEI del dispositivo")
    serial: str | None = Field(
        default=None, max_length=120, description="Número de serie")
    marca: str | None = Field(
        default=None, max_length=80, description="Marca comercial")
    modelo: str | None = Field(
        default=None, max_length=120, description="Modelo detallado")
    categoria: str | None = Field(
        default=None, max_length=80, description="Categoría de catálogo")
    condicion: str | None = Field(
        default=None, max_length=60, description="Condición física")
    color: str | None = Field(
        default=None, max_length=60, description="Color principal")
    capacidad_gb: int | None = Field(
        default=None, ge=0, description="Capacidad de almacenamiento en GB")
    capacidad: str | None = Field(
        default=None, max_length=80, description="Capacidad descriptiva")
    estado_comercial: CommercialState = Field(default=CommercialState.NUEVO)
    estado: str = Field(
        default="disponible",
        max_length=40,
        description="Estado logístico del producto (disponible, apartado, agotado, etc.)",
    )
    proveedor: str | None = Field(
        default=None, max_length=120, description="Proveedor principal")
    costo_unitario: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Costo neto por unidad",
    )
    costo_compra: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Costo de compra registrado para el catálogo",
    )
    margen_porcentaje: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Margen aplicado en porcentaje",
    )
    garantia_meses: int = Field(
        default=0, ge=0, description="Garantía ofrecida en meses")
    lote: str | None = Field(default=None, max_length=80,
                             description="Identificador de lote")
    fecha_compra: date | None = Field(
        default=None, description="Fecha de compra al proveedor")
    fecha_ingreso: date | None = Field(
        default=None, description="Fecha de ingreso al inventario")
    ubicacion: str | None = Field(
        default=None, max_length=120, description="Ubicación física en la sucursal")
    descripcion: str | None = Field(
        default=None,
        max_length=1024,
        description="Descripción extendida o notas del producto",
    )
    imagen_url: str | None = Field(
        default=None,
        max_length=255,
        description="URL de la imagen representativa del producto",
    )
    completo: bool = Field(
        default=True,
        description="Indica si la ficha del producto cuenta con todos los datos obligatorios",
    )

    @model_validator(mode="after")
    def _validate_stock_thresholds(self) -> "DeviceBase":
        if self.reorder_point < self.minimum_stock:
            raise ValueError(
                "El punto de reorden debe ser mayor o igual al stock mínimo."
            )
        return self

    @field_serializer("unit_price")
    @classmethod
    def _serialize_unit_price(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("precio_venta")
    @classmethod
    def _serialize_sale_price(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("costo_unitario")
    @classmethod
    def _serialize_cost(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("costo_compra")
    @classmethod
    def _serialize_purchase_cost(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("margen_porcentaje")
    @classmethod
    def _serialize_margin(cls, value: Decimal) -> float:
        return float(value)

    @field_validator("imei")
    @classmethod
    def validate_imei(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if normalized and not (10 <= len(normalized) <= 18):
            raise ValueError("IMEI inválido")
        return normalized or None

    @field_validator("serial")
    @classmethod
    def validate_serial(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if normalized and len(normalized) < 4:
            raise ValueError("Número de serie inválido")
        return normalized or None

    @model_validator(mode="before")
    @classmethod
    def _map_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "precio_venta" in data and "unit_price" not in data:
                data["unit_price"] = data["precio_venta"]
            if "costo_compra" in data and "costo_unitario" not in data:
                data["costo_unitario"] = data["costo_compra"]
        return data

    @model_validator(mode="after")
    def _sync_aliases(self) -> "DeviceBase":
        object.__setattr__(self, "precio_venta", self.unit_price)
        object.__setattr__(self, "costo_compra", self.costo_unitario)
        return self

    @field_validator(
        "marca",
        "modelo",
        "color",
        "categoria",
        "condicion",
        "capacidad",
        "estado",
        "proveedor",
        "lote",
        "ubicacion",
        "descripcion",
        "imagen_url",
        mode="before",
    )
    @classmethod
    def _normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("estado")
    @classmethod
    def _default_estado(cls, value: str | None) -> str:
        if not value:
            return "disponible"
        return value


class DeviceCreate(DeviceBase):
    """Datos necesarios para registrar un dispositivo."""


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    quantity: int | None = Field(default=None, ge=0)
    unit_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    precio_venta: Decimal | None = Field(default=None, ge=Decimal("0"))
    imei: str | None = Field(default=None, max_length=18)
    serial: str | None = Field(default=None, max_length=120)
    marca: str | None = Field(default=None, max_length=80)
    modelo: str | None = Field(default=None, max_length=120)
    categoria: str | None = Field(default=None, max_length=80)
    condicion: str | None = Field(default=None, max_length=60)
    color: str | None = Field(default=None, max_length=60)
    capacidad_gb: int | None = Field(default=None, ge=0)
    capacidad: str | None = Field(default=None, max_length=80)
    estado_comercial: CommercialState | None = Field(default=None)
    estado: str | None = Field(default=None, max_length=40)
    proveedor: str | None = Field(default=None, max_length=120)
    costo_unitario: Decimal | None = Field(default=None, ge=Decimal("0"))
    costo_compra: Decimal | None = Field(default=None, ge=Decimal("0"))
    margen_porcentaje: Decimal | None = Field(default=None, ge=Decimal("0"))
    garantia_meses: int | None = Field(default=None, ge=0)
    lote: str | None = Field(default=None, max_length=80)
    fecha_compra: date | None = Field(default=None)
    fecha_ingreso: date | None = Field(default=None)
    ubicacion: str | None = Field(default=None, max_length=120)
    descripcion: str | None = Field(default=None, max_length=1024)
    imagen_url: str | None = Field(default=None, max_length=255)
    completo: bool | None = Field(default=None)
    minimum_stock: int | None = Field(default=None, ge=0)
    reorder_point: int | None = Field(default=None, ge=0)
    warehouse_id: int | None = Field(default=None, ge=1)

    @model_validator(mode="before")
    @classmethod
    def _map_update_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "precio_venta" in data and "unit_price" not in data:
                data["unit_price"] = data["precio_venta"]
            if "costo_compra" in data and "costo_unitario" not in data:
                data["costo_unitario"] = data["costo_compra"]
        return data

    @model_validator(mode="after")
    def _validate_partial_thresholds(self) -> "DeviceUpdate":
        minimum = self.minimum_stock
        reorder = self.reorder_point
        if minimum is not None and reorder is not None and reorder < minimum:
            raise ValueError(
                "El punto de reorden debe ser mayor o igual al stock mínimo."
            )
        return self

    @field_validator("imei")
    @classmethod
    def validate_update_imei(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if normalized and not (10 <= len(normalized) <= 18):
            raise ValueError("IMEI inválido")
        return normalized or None

    @field_validator("serial")
    @classmethod
    def validate_update_serial(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if normalized and len(normalized) < 4:
            raise ValueError("Número de serie inválido")
        return normalized or None

    @field_validator(
        "marca",
        "modelo",
        "color",
        "categoria",
        "condicion",
        "capacidad",
        "estado",
        "proveedor",
        "lote",
        "ubicacion",
        "descripcion",
        "imagen_url",
        mode="before",
    )
    @classmethod
    def _normalize_update_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None


class DeviceResponse(DeviceBase):
    id: int
    store_id: int
    identifier: DeviceIdentifierResponse | None = Field(default=None)
    warehouse_name: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field(return_type=float)  # type: ignore[misc]
    def inventory_value(self) -> float:
        return float(self.quantity * self.unit_price)

    @computed_field(return_type=int)  # type: ignore[misc]
    def variant_count(self) -> int:
        variants = getattr(self, "variants", None)
        if variants is None:
            return 0
        try:
            return len(list(variants))
        except TypeError:
            return 0

    @computed_field(return_type=bool)  # type: ignore[misc]
    def has_variants(self) -> bool:
        return self.variant_count > 0

    @computed_field(return_type=str | None)
    def almacen(self) -> str | None:
        warehouse = getattr(self, "warehouse", None)
        if warehouse:
            return getattr(warehouse, "name", None)
        return self.warehouse_name

    @computed_field(alias="warehouse_name", return_type=str | None)
    def warehouse_display(self) -> str | None:
        warehouse = getattr(self, "warehouse", None)
        if warehouse:
            return getattr(warehouse, "name", None)
        return self.warehouse_name


class CatalogProDeviceResponse(DeviceResponse):
    store_name: str

    model_config = ConfigDict(from_attributes=True)


class DeviceSearchFilters(BaseModel):
    imei: str | None = Field(default=None, max_length=18)
    serial: str | None = Field(default=None, max_length=120)
    capacidad_gb: int | None = Field(default=None, ge=0)
    color: str | None = Field(default=None, max_length=60)
    marca: str | None = Field(default=None, max_length=80)
    modelo: str | None = Field(default=None, max_length=120)
    categoria: str | None = Field(default=None, max_length=80)
    condicion: str | None = Field(default=None, max_length=60)
    estado_comercial: CommercialState | None = Field(default=None)
    estado: str | None = Field(default=None, max_length=40)
    ubicacion: str | None = Field(default=None, max_length=120)
    proveedor: str | None = Field(default=None, max_length=120)
    fecha_ingreso_desde: date | None = Field(default=None)
    fecha_ingreso_hasta: date | None = Field(default=None)

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    @field_validator("imei", "serial", "color", "marca", "modelo", mode="before")
    @classmethod
    def _normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("estado_comercial", mode="before")
    @classmethod
    def _normalize_estado_comercial(
        cls, value: CommercialState | str | None
    ) -> CommercialState | None:
        if value is None:
            return None
        if isinstance(value, CommercialState):
            return value
        normalized = str(value).strip()
        if not normalized:
            return None
        try:
            return CommercialState(normalized)
        except ValueError:
            candidates = {normalized.lower(), normalized.upper()}
            for candidate in candidates:
                try:
                    return CommercialState(candidate)
                except ValueError:
                    continue
            raise ValueError("estado_comercial_invalido")

    @field_validator("categoria", "condicion", "estado", "ubicacion", "proveedor", mode="before")
    @classmethod
    def _normalize_additional_filters(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None
