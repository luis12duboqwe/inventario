"""Esquemas Pydantic centralizados para la API de Softmobile Central."""
from __future__ import annotations

import enum
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    WithJsonSchema,
    computed_field,
    field_serializer,
    field_validator,
    model_validator,
    model_serializer,
)

from ..models import (
    BackupComponent,
    BackupMode,
    CashEntryType,
    CashSessionStatus,
    CommercialState,
    RecurringOrderType,
    MovementType,
    PaymentMethod,
    PurchaseStatus,
    RepairPartSource,
    RepairStatus,
    InventoryState,
    SyncMode,
    SyncOutboxPriority,
    SyncOutboxStatus,
    SyncQueueStatus,
    SyncStatus,
    TransferStatus,
    CustomerLedgerEntryType,
    SystemLogLevel,
)
from ..utils import audit as audit_utils


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


class StoreBase(BaseModel):
    name: str = Field(..., max_length=120,
                      description="Nombre visible de la sucursal")
    location: str | None = Field(
        default=None, max_length=255, description="Dirección física o referencia de la sucursal"
    )
    phone: str | None = Field(
        default=None, max_length=30, description="Teléfono de contacto principal"
    )
    manager: str | None = Field(
        default=None, max_length=120, description="Responsable operativo de la sucursal"
    )
    status: str = Field(
        default="activa", max_length=30, description="Estado operativo de la sucursal"
    )
    timezone: str = Field(default="UTC", max_length=50,
                          description="Zona horaria de la sucursal")


class StoreCreate(StoreBase):
    """Carga de datos necesaria para registrar una nueva sucursal."""

    code: str | None = Field(
        default=None,
        max_length=20,
        description="Código interno único de la sucursal",
    )


class StoreUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    manager: str | None = Field(default=None, max_length=120)
    status: str | None = Field(default=None, max_length=30)
    code: str | None = Field(default=None, max_length=20)
    timezone: str | None = Field(default=None, max_length=50)


class StoreResponse(StoreBase):
    id: int
    code: str
    created_at: datetime
    inventory_value: Decimal = Field(default=Decimal("0"))

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("inventory_value")
    @classmethod
    def _serialize_inventory_value(cls, value: Decimal) -> float:
        return float(value)


class DeviceBase(BaseModel):
    sku: str = Field(..., max_length=80,
                     description="Identificador único del producto")
    name: str = Field(..., max_length=120,
                      description="Descripción del dispositivo")
    quantity: int = Field(
        default=0, ge=0, description="Cantidad disponible en inventario")
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


class ProductVariantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    variant_sku: str = Field(..., min_length=1, max_length=80)
    barcode: str | None = Field(default=None, max_length=120)
    unit_price_override: Decimal | None = Field(default=None, ge=Decimal("0"))
    is_default: bool = Field(default=False)
    is_active: bool = Field(default=True)

    @field_serializer("unit_price_override")
    @classmethod
    def _serialize_price(cls, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)


class ProductVariantCreate(ProductVariantBase):
    pass


class ProductVariantUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    variant_sku: str | None = Field(default=None, max_length=80)
    barcode: str | None = Field(default=None, max_length=120)
    unit_price_override: Decimal | None = Field(default=None, ge=Decimal("0"))
    is_default: bool | None = Field(default=None)
    is_active: bool | None = Field(default=None)

    @field_serializer("unit_price_override")
    @classmethod
    def _serialize_update_price(cls, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)


class ProductVariantResponse(ProductVariantBase):
    id: int
    device_id: int
    store_id: int
    device_sku: str
    device_name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductBundleItemBase(BaseModel):
    device_id: int = Field(..., ge=1)
    variant_id: int | None = Field(default=None, ge=1)
    quantity: int = Field(default=1, ge=1)


class ProductBundleItemCreate(ProductBundleItemBase):
    pass


class ProductBundleItemResponse(ProductBundleItemBase):
    id: int
    variant_name: str | None = Field(default=None)
    device_sku: str
    device_name: str

    model_config = ConfigDict(from_attributes=True)


class ProductBundleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    bundle_sku: str = Field(..., min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    base_price: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    is_active: bool = Field(default=True)

    @field_serializer("base_price")
    @classmethod
    def _serialize_base_price(cls, value: Decimal) -> float:
        return float(value)


class ProductBundleCreate(ProductBundleBase):
    store_id: int | None = Field(default=None, ge=1)
    items: list[ProductBundleItemCreate] = Field(default_factory=list)


class ProductBundleUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    bundle_sku: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    base_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    is_active: bool | None = Field(default=None)
    store_id: int | None = Field(default=None, ge=1)
    items: list[ProductBundleItemCreate] | None = Field(default=None)

    @field_serializer("base_price")
    @classmethod
    def _serialize_update_price(cls, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)


class ProductBundleResponse(ProductBundleBase):
    id: int
    store_id: int | None
    created_at: datetime
    updated_at: datetime
    items: list[ProductBundleItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)




class PriceListBase(BaseModel):
    """Información común de una lista de precios corporativa."""

    name: str = Field(
        ...,
        min_length=3,
        max_length=120,
        description="Nombre visible para identificar la lista de precios.",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Descripción opcional del alcance o uso de la lista.",
    )
    priority: int = Field(
        default=100,
        ge=0,
        le=10000,
        description="Prioridad corporativa (0 = máxima prioridad).",
    )
    is_active: bool = Field(
        default=True,
        description="Indica si la lista está habilitada para resolver precios.",
    )
    store_id: int | None = Field(
        default=None,
        ge=1,
        description="Identificador de la sucursal asociada, cuando aplica.",
    )
    customer_id: int | None = Field(
        default=None,
        ge=1,
        description="Cliente corporativo preferente ligado a la lista.",
    )
    currency: str = Field(
        default="MXN",
        min_length=3,
        max_length=10,
        description="Moneda ISO 4217 en la que se expresan los precios.",
    )
    valid_from: date | None = Field(
        default=None,
        description="Fecha a partir de la cual la lista entra en vigor.",
    )
    valid_until: date | None = Field(
        default=None,
        description="Fecha límite de vigencia de la lista de precios.",
    )
    starts_at: datetime | None = Field(
        default=None,
        description="Fecha de inicio de vigencia en hora exacta (UTC).",
    )
    ends_at: datetime | None = Field(
        default=None,
        description="Fecha de término de vigencia en hora exacta (UTC).",
    )

    @field_validator("name", mode="before")
    @classmethod
    def _normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("El nombre debe tener al menos 3 caracteres.")
        return normalized

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("currency", mode="before")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) < 3:
            raise ValueError("La moneda debe tener al menos 3 caracteres.")
        return normalized

    @model_validator(mode="after")
    def _validate_dates(self) -> "PriceListBase":
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_from > self.valid_until
        ):
            raise ValueError(
                "La fecha de inicio no puede ser posterior a la fecha de fin."
            )
        if (
            self.starts_at is not None
            and self.ends_at is not None
            and self.ends_at <= self.starts_at
        ):
            raise ValueError("La fecha de término debe ser posterior al inicio.")
        return self


class PriceListCreate(PriceListBase):
    """Carga útil para registrar una nueva lista de precios."""


class PriceListUpdate(BaseModel):
    """Campos opcionales disponibles para actualizar una lista de precios."""

    name: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    priority: int | None = Field(default=None, ge=0, le=10000)
    is_active: bool | None = Field(default=None)
    store_id: int | None = Field(default=None, ge=1)
    customer_id: int | None = Field(default=None, ge=1)
    currency: str | None = Field(default=None, min_length=3, max_length=10)
    valid_from: date | None = Field(default=None)
    valid_until: date | None = Field(default=None)

    @field_validator("name", mode="before")
    @classmethod
    def _normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if normalized and len(normalized) < 3:
            raise ValueError("El nombre debe tener al menos 3 caracteres.")
        return normalized or None

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("currency", mode="before")
    @classmethod
    def _normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if len(normalized) < 3:
            raise ValueError("La moneda debe contener al menos 3 caracteres.")
        return normalized


class PriceListUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    priority: int | None = Field(default=None, ge=0, le=10000)
    is_active: bool | None = Field(default=None)
    store_id: int | None = Field(default=None, ge=1)
    customer_id: int | None = Field(default=None, ge=1)
    starts_at: datetime | None = Field(default=None)
    ends_at: datetime | None = Field(default=None)
    valid_from: date | None = Field(default=None)
    valid_until: date | None = Field(default=None)

    @model_validator(mode="after")
    def _validate_dates(self) -> "PriceListUpdate":
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_from > self.valid_until
        ):
            raise ValueError(
                "La fecha de inicio no puede ser posterior a la fecha de fin."
            )
        if (
            self.starts_at is not None
            and self.ends_at is not None
            and self.ends_at <= self.starts_at
        ):
            raise ValueError("La fecha de término debe ser posterior al inicio.")
        return self


class PriceListItemBase(BaseModel):
    """Definición de un precio para un producto dentro de una lista."""

    device_id: int = Field(
        ...,
        ge=1,
        description="Identificador del dispositivo dentro del catálogo corporativo.",
    )
    price: Decimal = Field(
        ...,
        gt=Decimal("0"),
        description="Precio específico definido en la lista.",
    )
    discount_percentage: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("100"),
        description="Descuento porcentual adicional aplicado al precio base.",
    )
    currency: str = Field(
        default="MXN",
        min_length=3,
        max_length=8,
        description="Moneda ISO 4217 asociada al precio.",
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Notas internas sobre la regla de precios.",
    )

    @field_validator("currency", mode="before")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) < 3:
            raise ValueError("La moneda debe contener al menos 3 caracteres.")
        return normalized

    @field_validator("notes", mode="before")
    @classmethod
    def _normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class PriceListItemCreate(PriceListItemBase):
    """Carga útil para agregar un producto a una lista de precios."""


class PriceListItemUpdate(BaseModel):
    """Campos disponibles para actualizar un precio de catálogo."""

    price: Decimal | None = Field(default=None, gt=Decimal("0"))
    currency: str | None = Field(default=None, min_length=3, max_length=8)
    discount_percentage: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("100"),
    )
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("currency", mode="before")
    @classmethod
    def _normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if len(normalized) < 3:
            raise ValueError("La moneda debe contener al menos 3 caracteres.")
        return normalized

    @field_validator("notes", mode="before")
    @classmethod
    def _normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def _ensure_valid_price(self) -> "PriceListItemUpdate":
        if self.price is not None and self.price <= Decimal("0"):
            raise ValueError("El precio debe ser mayor a cero.")
        return self


class PriceListItemResponse(PriceListItemBase):
    id: int
    price_list_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("price")
    @classmethod
    def _serialize_price(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("discount_percentage")
    @classmethod
    def _serialize_discount(cls, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)


class PriceListResponse(PriceListBase):
    id: int
    scope: str
    created_at: datetime
    updated_at: datetime
    items: list[PriceListItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

class PriceResolution(BaseModel):
    """Resultado de resolver un precio con base en listas disponibles."""

    device_id: int = Field(..., ge=1)
    price_list_id: int | None = Field(default=None, ge=1)
    price_list_name: str | None = Field(default=None, max_length=120)
    scope: Literal[
        "store_customer",
        "customer",
        "store",
        "global",
        "fallback",
    ] = Field(..., description="Ámbito de la lista aplicada al cálculo.")
    source: Literal["price_list", "fallback"] = Field(
        ..., description="Origen del precio devuelto."
    )
    currency: str = Field(..., min_length=3, max_length=10)
    base_price: Decimal = Field(..., ge=Decimal("0"))
    discount_percentage: Decimal | None = Field(
        default=None, ge=Decimal("0"), le=Decimal("100")
    )
    final_price: Decimal = Field(..., ge=Decimal("0"))
    valid_from: date | None = None
    valid_until: date | None = None

    @field_serializer("base_price")
    @classmethod
    def _serialize_base_price(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("discount_percentage")
    @classmethod
    def _serialize_discount(cls, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)

    @field_serializer("final_price")
    @classmethod
    def _serialize_final_price(cls, value: Decimal) -> float:
        return float(value)

class PriceEvaluationRequest(BaseModel):
    device_id: int = Field(..., ge=1)
    store_id: int | None = Field(default=None, ge=1)
    customer_id: int | None = Field(default=None, ge=1)


class PriceEvaluationResponse(BaseModel):
    device_id: int
    price_list_id: int | None = None
    scope: str | None = None
    price: float | None = None
    currency: str | None = None

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
    validacion_resumen: "ImportValidationSummary | None" = None


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


class ImportValidationSummary(BaseModel):
    registros_revisados: int
    advertencias: int
    errores: int
    campos_faltantes: list[str] = Field(default_factory=list)
    tiempo_total: float | None = None


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


class CatalogProDeviceResponse(DeviceResponse):
    store_name: str

    model_config = ConfigDict(from_attributes=True)


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
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_serializer
    def _serialize(self) -> dict[str, Any]:  # pragma: no cover - mapeo directo
        return {
            "id": self.id,
            "codigo": self.code,
            "sucursal_id": self.store_id,
            "fecha_creacion": self.created_at,
            "fecha_actualizacion": self.updated_at,
        }


class DeviceBinAssignmentResponse(BaseModel):
    producto_id: int = Field(..., ge=1)
    bin: WMSBinResponse
    asignado_en: datetime
    desasignado_en: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class StoreMembershipBase(BaseModel):
    user_id: int = Field(..., ge=1)
    store_id: int = Field(..., ge=1)
    can_create_transfer: bool = Field(default=False)
    can_receive_transfer: bool = Field(default=False)


class StoreMembershipResponse(StoreMembershipBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StoreMembershipUpdate(StoreMembershipBase):
    """Actualiza los permisos de pertenencia de un usuario en una sucursal."""


class ContactHistoryEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
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


class CustomerBase(BaseModel):
    contact_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=120)
    phone: str = Field(..., min_length=5, max_length=40)
    address: str | None = Field(default=None, max_length=255)
    customer_type: str = Field(
        default="minorista", min_length=3, max_length=30)
    status: str = Field(default="activo", min_length=3, max_length=20)
    credit_limit: Decimal = Field(default=Decimal("0"))
    notes: str | None = Field(default=None, max_length=500)
    outstanding_debt: Decimal = Field(default=Decimal("0"))
    history: list[ContactHistoryEntry] = Field(default_factory=list)

    @field_validator(
        "contact_name",
        "email",
        "phone",
        "address",
        "customer_type",
        "status",
        "notes",
        mode="before",
    )
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_serializer("outstanding_debt")
    @classmethod
    def _serialize_debt(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("credit_limit")
    @classmethod
    def _serialize_credit_limit(cls, value: Decimal) -> float:
        return float(value)

    @field_validator("phone", mode="after")
    @classmethod
    def _ensure_phone(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El teléfono del cliente es obligatorio.")
        return normalized


class CustomerCreate(CustomerBase):
    name: str = Field(..., max_length=120)

    @field_validator("name")
    @classmethod
    def _normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El nombre es obligatorio.")
        return normalized


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    contact_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=255)
    customer_type: str | None = Field(default=None, max_length=30)
    status: str | None = Field(default=None, max_length=20)
    credit_limit: Decimal | None = Field(default=None)
    notes: str | None = Field(default=None, max_length=500)
    outstanding_debt: Decimal | None = Field(default=None)
    history: list[ContactHistoryEntry] | None = Field(default=None)

    @field_validator(
        "name",
        "contact_name",
        "email",
        "phone",
        "address",
        "customer_type",
        "status",
        "notes",
        mode="before",
    )
    @classmethod
    def _normalize_update_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CustomerResponse(CustomerBase):
    id: int
    name: str
    last_interaction_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerNoteCreate(BaseModel):
    note: str = Field(..., min_length=3, max_length=255)

    @field_validator("note", mode="before")
    @classmethod
    def _normalize_note(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("La nota del cliente es obligatoria.")
        return normalized


class CustomerPaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=Decimal("0"))
    method: str = Field(default="manual", min_length=3, max_length=40)
    reference: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=255)
    sale_id: int | None = Field(default=None, ge=1)

    @field_validator("method", mode="before")
    @classmethod
    def _normalize_method(cls, value: str | None) -> str:
        if value is None:
            return "manual"
        normalized = value.strip()
        if not normalized:
            raise ValueError("Indica un método de pago válido.")
        return normalized

    @field_validator("reference", "note", mode="before")
    @classmethod
    def _normalize_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CustomerLedgerEntryResponse(BaseModel):
    id: int
    entry_type: CustomerLedgerEntryType
    reference_type: str | None
    reference_id: str | None
    amount: float
    balance_after: float
    note: str | None
    details: dict[str, Any]
    created_at: datetime
    created_by: str | None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("amount")
    @classmethod
    def _serialize_amount(cls, value: Decimal) -> float:
        return float(value)


class CustomerDebtSnapshot(BaseModel):
    previous_balance: Decimal
    new_charges: Decimal
    payments_applied: Decimal
    remaining_balance: Decimal

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_serializer("previous_balance", "new_charges", "payments_applied", "remaining_balance")
    @classmethod
    def _serialize_snapshot_decimal(cls, value: Decimal) -> float:
        return float(value)


class CreditScheduleEntry(BaseModel):
    sequence: int
    due_date: datetime
    amount: Decimal
    status: Literal["pending", "due_soon", "overdue"]
    reminder: str | None = None

    @field_serializer("amount")
    @classmethod
    def _serialize_amount(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("due_date")
    @classmethod
    def _serialize_due_date(cls, value: datetime) -> str:
        return value.isoformat()


class CustomerPaymentReceiptResponse(BaseModel):
    ledger_entry: CustomerLedgerEntryResponse
    debt_summary: CustomerDebtSnapshot
    credit_schedule: list[CreditScheduleEntry] = Field(default_factory=list)
    receipt_pdf_base64: str


class CustomerSaleSummary(BaseModel):
    sale_id: int
    store_id: int
    store_name: str | None
    payment_method: PaymentMethod
    status: str
    subtotal_amount: float
    tax_amount: float
    total_amount: float
    created_at: datetime


class CustomerInvoiceSummary(BaseModel):
    sale_id: int
    invoice_number: str
    total_amount: float
    status: str
    created_at: datetime
    store_id: int


class CustomerFinancialSnapshot(BaseModel):
    credit_limit: float
    outstanding_debt: float
    available_credit: float
    total_sales_credit: float
    total_payments: float


class CustomerSummaryResponse(BaseModel):
    customer: CustomerResponse
    totals: CustomerFinancialSnapshot
    sales: list[CustomerSaleSummary]
    invoices: list[CustomerInvoiceSummary]
    payments: list[CustomerLedgerEntryResponse]
    ledger: list[CustomerLedgerEntryResponse]


class PaymentCenterSummary(BaseModel):
    collections_today: float = 0.0
    collections_month: float = 0.0
    pending_balance: float = 0.0
    refunds_month: float = 0.0


class PaymentCenterTransaction(BaseModel):
    id: int
    type: Literal["PAYMENT", "REFUND", "CREDIT_NOTE"]
    amount: float
    created_at: datetime
    order_id: int | None = None
    order_number: str | None = None
    customer_id: int
    customer_name: str
    method: str | None = None
    note: str | None = None
    status: Literal["POSTED", "VOID"] = "POSTED"


class PaymentCenterResponse(BaseModel):
    summary: PaymentCenterSummary
    transactions: list[PaymentCenterTransaction]


class PaymentCenterPaymentCreate(CustomerPaymentCreate):
    customer_id: int = Field(gt=0)


class PaymentCenterRefundCreate(BaseModel):
    customer_id: int = Field(gt=0)
    amount: Decimal = Field(..., gt=Decimal("0"))
    method: str = Field(min_length=3, max_length=40)
    reason: str = Field(min_length=3, max_length=120)
    note: str | None = Field(default=None, max_length=255)
    sale_id: int | None = Field(default=None, ge=1)

    @field_validator("method", "reason", mode="before")
    @classmethod
    def _normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El campo es obligatorio")
        return normalized

    @field_validator("note", mode="before")
    @classmethod
    def _normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class PaymentCenterCreditNoteLine(BaseModel):
    description: str = Field(min_length=1, max_length=160)
    quantity: int = Field(default=1, ge=0)
    amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_description(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("La descripción es obligatoria")
        return normalized


class PaymentCenterCreditNoteCreate(BaseModel):
    customer_id: int = Field(gt=0)
    lines: list[PaymentCenterCreditNoteLine]
    total: Decimal = Field(..., gt=Decimal("0"))
    note: str | None = Field(default=None, max_length=255)
    sale_id: int | None = Field(default=None, ge=1)

    @field_validator("lines")
    @classmethod
    def _ensure_lines(cls, value: list[PaymentCenterCreditNoteLine]) -> list[PaymentCenterCreditNoteLine]:
        if not value:
            raise ValueError(
                "La nota de crédito requiere al menos un concepto")
        return value

    @field_validator("note", mode="before")
    @classmethod
    def _normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CustomerPortfolioFilters(BaseModel):
    category: Literal["delinquent", "frequent"]
    date_from: date | None = None
    date_to: date | None = None
    limit: int = Field(default=50, ge=1, le=500)


class CustomerPortfolioTotals(BaseModel):
    customers: int
    moroso_flagged: int
    outstanding_debt: float
    sales_total: float


class CustomerPortfolioItem(BaseModel):
    customer_id: int
    name: str
    status: str
    customer_type: str
    credit_limit: float
    outstanding_debt: float
    available_credit: float
    sales_total: float
    sales_count: int
    last_sale_at: datetime | None
    last_interaction_at: datetime | None


class CustomerPortfolioReport(BaseModel):
    generated_at: datetime
    category: Literal["delinquent", "frequent"]
    filters: CustomerPortfolioFilters
    items: list[CustomerPortfolioItem]
    totals: CustomerPortfolioTotals


class CustomerLeaderboardEntry(BaseModel):
    customer_id: int
    name: str
    status: str
    customer_type: str
    sales_total: float
    sales_count: int
    last_sale_at: datetime | None
    outstanding_debt: float


class CustomerDelinquentSummary(BaseModel):
    customers_with_debt: int
    moroso_flagged: int
    total_outstanding_debt: float


class CustomerDashboardMetrics(BaseModel):
    generated_at: datetime
    months: int
    new_customers_per_month: list[DashboardChartPoint]
    top_customers: list[CustomerLeaderboardEntry]
    delinquent_summary: CustomerDelinquentSummary


class SupplierBase(BaseModel):
    contact_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=500)
    outstanding_debt: Decimal = Field(default=Decimal("0"))
    history: list[ContactHistoryEntry] = Field(default_factory=list)

    @field_validator("contact_name", "email", "phone", "address", "notes", mode="before")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_serializer("outstanding_debt")
    @classmethod
    def _serialize_debt(cls, value: Decimal) -> float:
        return float(value)


class SupplierCreate(SupplierBase):
    name: str = Field(..., max_length=120)

    @field_validator("name")
    @classmethod
    def _normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El nombre es obligatorio.")
        return normalized


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    contact_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=500)
    outstanding_debt: Decimal | None = Field(default=None)
    history: list[ContactHistoryEntry] | None = Field(default=None)

    @field_validator("name", "contact_name", "email", "phone", "address", "notes", mode="before")
    @classmethod
    def _normalize_update_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class SupplierResponse(SupplierBase):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierBatchBase(BaseModel):
    model_name: str = Field(..., max_length=120)
    batch_code: str = Field(..., max_length=80)
    unit_cost: Decimal = Field(..., ge=Decimal("0"))
    quantity: int = Field(default=0, ge=0)
    purchase_date: date
    notes: str | None = Field(default=None, max_length=255)
    store_id: int | None = Field(default=None, ge=1)
    device_id: int | None = Field(default=None, ge=1)

    model_config = ConfigDict(protected_namespaces=())

    @field_validator("model_name", "batch_code", "notes", mode="before")
    @classmethod
    def _normalize_batch_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_serializer("unit_cost")
    @classmethod
    def _serialize_unit_cost(cls, value: Decimal) -> float:
        return float(value)


class SupplierBatchCreate(SupplierBatchBase):
    """Datos requeridos para registrar un nuevo lote de proveedor."""


class SupplierBatchUpdate(BaseModel):
    model_name: str | None = Field(default=None, max_length=120)
    batch_code: str | None = Field(default=None, max_length=80)
    unit_cost: Decimal | None = Field(default=None, ge=Decimal("0"))
    quantity: int | None = Field(default=None, ge=0)
    purchase_date: date | None = None
    notes: str | None = Field(default=None, max_length=255)
    store_id: int | None = Field(default=None, ge=1)
    device_id: int | None = Field(default=None, ge=1)

    model_config = ConfigDict(protected_namespaces=())

    @field_validator("model_name", "batch_code", "notes", mode="before")
    @classmethod
    def _normalize_optional_batch_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class SupplierBatchResponse(SupplierBatchBase):
    id: int
    supplier_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class SupplierBatchOverviewItem(BaseModel):
    supplier_id: int
    supplier_name: str
    batch_count: int = Field(ge=0)
    total_quantity: int = Field(ge=0)
    total_value: float = Field(ge=0)
    latest_purchase_date: date
    latest_batch_code: str | None = None
    latest_unit_cost: float | None = Field(default=None, ge=0)


class TransferOrderItemBase(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)
    reservation_id: int | None = Field(default=None, ge=1)


class TransferOrderItemCreate(TransferOrderItemBase):
    """Elemento incluido en la creación de una orden de transferencia."""


class TransferOrderTransition(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


class TransferOrderCreate(BaseModel):
    origin_store_id: int = Field(..., ge=1)
    destination_store_id: int = Field(..., ge=1)
    reason: str | None = Field(default=None, max_length=255)
    items: list[TransferOrderItemCreate]

    @field_validator("reason")
    @classmethod
    def _normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("items")
    @classmethod
    def _ensure_items(cls, value: list[TransferOrderItemCreate]) -> list[TransferOrderItemCreate]:
        if not value:
            raise ValueError(
                "Debes incluir al menos un dispositivo en la transferencia.")
        return value


class TransferOrderItemResponse(TransferOrderItemBase):
    id: int
    transfer_order_id: int

    model_config = ConfigDict(from_attributes=True)


class TransferOrderResponse(BaseModel):
    id: int
    origin_store_id: int
    destination_store_id: int
    status: TransferStatus
    reason: str | None
    created_at: datetime
    updated_at: datetime
    dispatched_at: datetime | None
    received_at: datetime | None
    cancelled_at: datetime | None
    items: list[TransferOrderItemResponse]
    ultima_accion: AuditTrailInfo | None = None

    model_config = ConfigDict(from_attributes=True)


class TransferReportFilters(BaseModel):
    store_id: int | None = None
    origin_store_id: int | None = None
    destination_store_id: int | None = None
    status: TransferStatus | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class TransferReportDevice(BaseModel):
    sku: str | None
    name: str | None
    quantity: int


class TransferReportItem(BaseModel):
    id: int
    folio: str
    origin_store: str
    destination_store: str
    status: TransferStatus
    reason: str | None
    requested_at: datetime
    dispatched_at: datetime | None
    received_at: datetime | None
    cancelled_at: datetime | None
    requested_by: str | None
    dispatched_by: str | None
    received_by: str | None
    cancelled_by: str | None
    total_quantity: int
    devices: list[TransferReportDevice]
    ultima_accion: AuditTrailInfo | None = None


class TransferReportTotals(BaseModel):
    total_transfers: int
    pending: int
    in_transit: int
    completed: int
    cancelled: int
    total_quantity: int


class TransferReport(BaseModel):
    generated_at: datetime
    filters: TransferReportFilters
    totals: TransferReportTotals
    items: list[TransferReportItem]


class RoleResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    # El campo principal es username; aceptamos 'correo' como alias de entrada mediante _coerce_aliases.
    username: Annotated[str, Field(..., max_length=120)]
    full_name: Annotated[str | None, Field(default=None, max_length=120)]
    telefono: str | None = Field(default=None, max_length=30)

    model_config = ConfigDict(populate_by_name=True)

    @computed_field(alias="correo")
    @property
    def correo(self) -> str:
        return self.username

    @computed_field(alias="nombre")
    @property
    def nombre(self) -> str | None:
        return self.full_name

    @field_validator("username")
    @classmethod
    def _validate_username(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("El correo del usuario es obligatorio")
        return value.strip()

    @model_validator(mode="before")
    @classmethod
    def _coerce_aliases(cls, data: Any) -> Any:  # pragma: no cover - lógica simple
        """Permite aceptar claves alternativas (correo/nombre) sin usar validation_alias.

        Evita warnings de Pydantic v2 y mantiene compatibilidad con payloads históricos.
        """
        if not isinstance(data, dict):
            return data
        # username <= correo
        if "username" not in data and "correo" in data:
            data["username"] = data.get("correo")
        # full_name <= nombre
        if "full_name" not in data and "nombre" in data:
            data["full_name"] = data.get("nombre")
        return data


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    roles: list[str] = Field(default_factory=list)
    store_id: Annotated[int | None, Field(default=None, ge=1)]


class BootstrapStatusResponse(BaseModel):
    disponible: bool = Field(
        ...,
        description="Indica si el registro inicial de administrador está habilitado.",
    )
    usuarios_registrados: int = Field(
        ...,
        ge=0,
        description="Cantidad total de cuentas existentes en el sistema.",
    )


class UserRolesUpdate(BaseModel):
    roles: list[str] = Field(default_factory=list)


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserResponse(UserBase):
    id: int
    is_active: bool
    rol: str
    estado: str
    created_at: datetime
    roles: list[RoleResponse]
    store: StoreResponse | None = Field(default=None, exclude=True)
    ultima_accion: AuditTrailInfo | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("roles", mode="before")
    @classmethod
    def _flatten_roles(cls, value: Any) -> list[RoleResponse]:
        if value is None:
            return []
        flattened: list[RoleResponse] = []
        for item in value:
            if isinstance(item, RoleResponse):
                flattened.append(item)
                continue
            role_obj = getattr(item, "role", item)
            flattened.append(RoleResponse.model_validate(role_obj))
        return flattened

    @computed_field
    @property
    def store_id(self) -> int | None:
        store_obj = self.store
        if store_obj is None:
            return None
        return store_obj.id

    @computed_field
    @property
    def store_name(self) -> str | None:
        store_obj = self.store
        if store_obj is None:
            return None
        return store_obj.name

    @computed_field(alias="fecha_creacion")
    @property
    def fecha_creacion(self) -> datetime:
        return self.created_at

    @computed_field(alias="sucursal_id")
    @property
    def sucursal_id(self) -> int | None:
        return self.store_id

    @computed_field(alias="rol_id")
    @property
    def primary_role_id(self) -> int | None:
        if not self.roles:
            return None
        return self.roles[0].id


class UserUpdate(BaseModel):
    full_name: Annotated[str | None, Field(default=None, max_length=120)]
    telefono: str | None = Field(default=None, max_length=30)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    store_id: Annotated[int | None, Field(default=None, ge=1)]
    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def _coerce_aliases(cls, data: Any) -> Any:  # pragma: no cover - simple
        if not isinstance(data, dict):
            return data
        if "full_name" not in data and "nombre" in data:
            data["full_name"] = data.get("nombre")
        if "store_id" not in data and "sucursal_id" in data:
            data["store_id"] = data.get("sucursal_id")
        return data


class RoleModulePermission(BaseModel):
    module: str = Field(..., min_length=2, max_length=120)
    can_view: bool = Field(default=False)
    can_edit: bool = Field(default=False)
    can_delete: bool = Field(default=False)


class RolePermissionMatrix(BaseModel):
    role: str = Field(..., min_length=2, max_length=60)
    permissions: list[RoleModulePermission] = Field(default_factory=list)


class RolePermissionUpdate(BaseModel):
    permissions: list[RoleModulePermission] = Field(default_factory=list)


class UserDirectoryFilters(BaseModel):
    search: str | None = Field(default=None, max_length=120)
    role: str | None = Field(default=None, max_length=60)
    status: Literal["all", "active", "inactive", "locked"] = "all"
    store_id: int | None = Field(default=None, ge=1)


class UserDirectoryTotals(BaseModel):
    total: int
    active: int
    inactive: int
    locked: int


class UserDirectoryEntry(BaseModel):
    user_id: int = Field(alias="id")
    username: str
    full_name: str | None = Field(default=None)
    telefono: str | None = Field(default=None)
    rol: str
    estado: str
    is_active: bool
    roles: list[str] = Field(default_factory=list)
    store_id: int | None = Field(default=None)
    store_name: str | None = Field(default=None)
    last_login_at: datetime | None = None
    ultima_accion: AuditTrailInfo | None = None

    model_config = ConfigDict(populate_by_name=True)


class UserDirectoryReport(BaseModel):
    generated_at: datetime
    filters: UserDirectoryFilters
    totals: UserDirectoryTotals
    items: list[UserDirectoryEntry]


class UserDashboardActivity(BaseModel):
    id: int
    action: str
    created_at: datetime
    severity: Literal["info", "warning", "critical"]
    performed_by_id: int | None = None
    performed_by_name: str | None = None
    target_user_id: int | None = None
    target_username: str | None = None
    details: dict[str, Any] | None = None


class UserSessionSummary(BaseModel):
    session_id: int
    user_id: int
    username: str
    created_at: datetime
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    status: Literal["activa", "revocada", "expirada"]
    revoke_reason: str | None = None


class UserDashboardMetrics(BaseModel):
    generated_at: datetime
    totals: UserDirectoryTotals
    recent_activity: list[UserDashboardActivity] = Field(default_factory=list)
    active_sessions: list[UserSessionSummary] = Field(default_factory=list)
    audit_alerts: DashboardAuditAlerts


# // [PACK28-schemas]
class AuthLoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=3, max_length=128)
    otp: str | None = Field(default=None, min_length=6, max_length=6)


# // [PACK28-schemas]
class AuthLoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


# // [PACK28-schemas]
class AuthProfileResponse(UserResponse):
    name: str
    email: str | None = Field(default=None)
    role: str


class TokenResponse(BaseModel):
    access_token: str
    session_id: int
    token_type: str = "bearer"


class SessionLoginResponse(BaseModel):
    session_id: int
    detail: str


class PasswordRecoveryRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=120)


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., min_length=20, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordResetResponse(BaseModel):
    detail: str
    reset_token: str | None = Field(default=None)


class TokenPayload(BaseModel):
    # // [PACK28-schemas]
    sub: str
    name: str | None = None
    role: str | None = None
    iat: int
    exp: int
    jti: str
    sid: str | None = None
    token_type: str = Field(default="access")


class TokenVerificationRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=4096)


class TokenVerificationResponse(BaseModel):
    is_valid: bool = Field(...,
                           description="Indica si el token sigue siendo válido.")
    detail: str = Field(...,
                        description="Mensaje descriptivo del estado del token.")
    session_id: int | None = Field(
        default=None,
        description="Identificador interno de la sesión asociada al token.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Fecha de expiración registrada para la sesión.",
    )
    user: UserResponse | None = Field(
        default=None,
        description="Información del usuario cuando el token es válido.",
    )

    model_config = ConfigDict(from_attributes=True)


class TOTPSetupResponse(BaseModel):
    secret: str
    otpauth_url: str


class TOTPStatusResponse(BaseModel):
    is_active: bool
    activated_at: datetime | None
    last_verified_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class TOTPActivateRequest(BaseModel):
    """Payload para activar 2FA TOTP.

    Acepta alias comunes como otp/totp/token/otp_code sin generar warnings de alias.
    """

    code: str = Field(..., min_length=6, max_length=10)

    @model_validator(mode="before")
    @classmethod
    def _coerce_aliases(cls, data: Any) -> Any:  # pragma: no cover
        if not isinstance(data, dict):
            return data
        if "code" not in data:
            for key in ("otp", "totp", "token", "otp_code"):
                if key in data and data[key]:
                    data["code"] = data[key]
                    break
        return data


class ActiveSessionResponse(BaseModel):
    id: int
    user_id: int
    session_token: str
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    revoked_by_id: int | None
    revoke_reason: str | None
    user: UserResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class SessionRevokeRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=255)

    @model_validator(mode="before")
    @classmethod
    def _coerce_reason_alias(cls, data: Any) -> Any:  # pragma: no cover
        if isinstance(data, dict) and "reason" not in data:
            for alias in ("motivo", "revoke_reason"):
                if alias in data:
                    data["reason"] = data[alias]
                    break
        return data


class POSReturnItemRequest(BaseModel):
    """Item devuelto desde el POS identificable por producto, línea o IMEI."""

    sale_item_id: Annotated[
        int | None,
        Field(
            default=None,
            ge=1,
            validation_alias=AliasChoices(
                "sale_item_id",
                "saleItemId",
                "item_id",
                "itemId",
            ),
        ),
    ]
    product_id: Annotated[
        int | None,
        Field(
            default=None,
            ge=1,
            validation_alias=AliasChoices(
                "product_id",
                "productId",
                "device_id",
            ),
        ),
    ]
    imei: Annotated[
        str | None,
        Field(
            default=None,
            max_length=18,
            validation_alias=AliasChoices("imei", "imei_1"),
        ),
    ]
    qty: Annotated[
        int,
        Field(
            ...,
            ge=1,
            validation_alias=AliasChoices("quantity", "qty"),
        ),
    ]

    @model_validator(mode="after")
    def _ensure_identifier(self) -> "POSReturnItemRequest":
        if not (self.sale_item_id or self.product_id or self.imei):
            raise ValueError(
                "Debes proporcionar sale_item_id, product_id o imei para la devolución."
            )
        return self

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
    performed_by_id: int | None = None
    created_at: datetime
    unit_cost: Decimal | None = None
    store_inventory_value: Decimal
    # Propiedades calculadas disponibles en el modelo (usuario, sucursal_origen, sucursal_destino)
    usuario: str | None = None
    sucursal_origen: str | None = None
    sucursal_destino: str | None = None
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
            "usuario_id": self.performed_by_id,
            "usuario": self.usuario,
            "referencia_tipo": self.referencia_tipo,
            "referencia_id": self.referencia_id,
            "fecha": self.created_at,
            "unit_cost": self._serialize_unit_cost(self.unit_cost),
            "store_inventory_value": self._serialize_inventory_total(self.store_inventory_value),
            "ultima_accion": self.ultima_accion,
        }


class InventoryReservationCreate(BaseModel):
    store_id: int = Field(..., ge=1)
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)
    expires_at: datetime


class InventoryReceivingLine(BaseModel):
    device_id: int | None = Field(default=None, ge=1)
    imei: str | None = Field(default=None, min_length=3, max_length=64)
    serial: str | None = Field(default=None, min_length=3, max_length=64)
    quantity: int = Field(..., ge=1)
    unit_cost: Decimal | None = Field(default=None, ge=Decimal("0"))
    comment: str | None = Field(default=None, min_length=5, max_length=255)

    @model_validator(mode="after")
    def _ensure_identifier(self) -> "InventoryReceivingLine":
        if self.device_id is None and not (self.imei or self.serial):
            raise ValueError(
                "Cada línea debe incluir `device_id`, `imei` o `serial`."
            )
        return self


class InventoryReceivingRequest(BaseModel):
    store_id: int = Field(..., ge=1)
    note: str = Field(..., min_length=5, max_length=255)
    responsible: str | None = Field(default=None, max_length=120)
    reference: str | None = Field(default=None, max_length=120)
    lines: list[InventoryReceivingLine] = Field(..., min_length=1)


class InventoryReceivingSummary(BaseModel):
    lines: int = Field(..., ge=0)
    total_quantity: int = Field(..., ge=0)


class InventoryReceivingProcessed(BaseModel):
    identifier: str
    device_id: int
    quantity: int
    movement: MovementResponse


class InventoryReceivingResult(BaseModel):
    store_id: int
    processed: list[InventoryReceivingProcessed]
    totals: InventoryReceivingSummary


class InventoryCountLine(BaseModel):
    device_id: int | None = Field(default=None, ge=1)
    imei: str | None = Field(default=None, min_length=3, max_length=64)
    serial: str | None = Field(default=None, min_length=3, max_length=64)
    counted: int = Field(..., ge=0)
    comment: str | None = Field(default=None, min_length=5, max_length=255)

    @model_validator(mode="after")
    def _ensure_identifier(self) -> "InventoryCountLine":
        if self.device_id is None and not (self.imei or self.serial):
            raise ValueError(
                "Cada línea debe incluir `device_id`, `imei` o `serial`."
            )
        return self


class InventoryCycleCountRequest(BaseModel):
    store_id: int = Field(..., ge=1)
    note: str = Field(..., min_length=5, max_length=255)
    responsible: str | None = Field(default=None, max_length=120)
    reference: str | None = Field(default=None, max_length=120)
    lines: list[InventoryCountLine] = Field(..., min_length=1)


class InventoryCountDiscrepancy(BaseModel):
    device_id: int
    sku: str | None = None
    expected: int
    counted: int
    delta: int
    movement: MovementResponse | None = None
    identifier: str | None = None


class InventoryCycleCountSummary(BaseModel):
    lines: int = Field(..., ge=0)
    adjusted: int = Field(..., ge=0)
    matched: int = Field(..., ge=0)
    total_variance: int = Field(...)


class InventoryCycleCountResult(BaseModel):
    store_id: int
    adjustments: list[InventoryCountDiscrepancy]
    totals: InventoryCycleCountSummary


class InventoryReservationRenew(BaseModel):
    expires_at: datetime


class InventoryReservationResponse(BaseModel):
    id: int
    store_id: int
    device_id: int
    status: InventoryState
    initial_quantity: int
    quantity: int
    reason: str
    resolution_reason: str | None
    reference_type: str | None
    reference_id: str | None
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    reserved_by_id: int | None = None
    resolved_by_id: int | None = None
    resolved_at: datetime | None = None
    consumed_at: datetime | None = None
    device: DeviceResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class InventorySummary(BaseModel):
    store_id: int
    store_name: str
    total_items: int
    total_value: Decimal
    devices: list[DeviceResponse]

    @field_serializer("total_value")
    @classmethod
    def _serialize_total_value(cls, value: Decimal) -> float:
        return float(value)


class InventoryAvailabilityStore(BaseModel):
    store_id: int
    store_name: str
    quantity: int


class InventoryAvailabilityRecord(BaseModel):
    reference: str
    sku: str | None = None
    product_name: str
    device_ids: list[int]
    total_quantity: int
    stores: list[InventoryAvailabilityStore]


class InventoryAvailabilityResponse(BaseModel):
    generated_at: datetime
    items: list[InventoryAvailabilityRecord]

    model_config = ConfigDict(from_attributes=True)


class InventoryCurrentStore(BaseModel):
    store_id: int
    store_name: str
    device_count: int
    total_units: int
    total_value: Decimal

    @field_serializer("total_value")
    @classmethod
    def _serialize_current_value(cls, value: Decimal) -> float:
        return float(value)


class InventoryCurrentReport(BaseModel):
    stores: list[InventoryCurrentStore]
    totals: InventoryTotals


class InventoryIntegrityDeviceStatus(BaseModel):
    store_id: int
    store_name: str | None
    device_id: int
    sku: str | None
    quantity_actual: int
    quantity_calculada: int
    costo_actual: Decimal
    costo_calculado: Decimal
    last_movement_id: int | None
    last_movement_fecha: datetime | None
    issues: list[str] = Field(default_factory=list)

    @field_serializer("costo_actual")
    @classmethod
    def _serialize_costo_actual(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("costo_calculado")
    @classmethod
    def _serialize_costo_calculado(cls, value: Decimal) -> float:
        return float(value)


class InventoryIntegritySummary(BaseModel):
    dispositivos_evaluados: int
    dispositivos_inconsistentes: int
    discrepancias_totales: int


class InventoryIntegrityReport(BaseModel):
    resumen: InventoryIntegritySummary
    dispositivos: list[InventoryIntegrityDeviceStatus]


class StoreValueMetric(BaseModel):
    store_id: int
    store_name: str
    device_count: int
    total_units: int
    total_value: Decimal

    @field_serializer("total_value")
    @classmethod
    def _serialize_metric_value(cls, value: Decimal) -> float:
        return float(value)


class LowStockDevice(BaseModel):
    store_id: int
    store_name: str
    device_id: int
    sku: str
    name: str
    quantity: int
    unit_price: Decimal
    minimum_stock: int = Field(default=0, ge=0)
    reorder_point: int = Field(default=0, ge=0)

    @field_serializer("unit_price")
    @classmethod
    def _serialize_low_stock_price(cls, value: Decimal) -> float:
        return float(value)

    @computed_field(return_type=float)  # type: ignore[misc]
    def inventory_value(self) -> float:
        return float(self.quantity * self.unit_price)

    @computed_field(return_type=int)  # type: ignore[misc]
    def reorder_gap(self) -> int:
        return max(self.reorder_point - self.quantity, 0)


class InventoryAlertDevice(LowStockDevice):
    severity: Literal["critical", "warning", "notice"]
    projected_days: int | None = None
    average_daily_sales: float | None = None
    trend: str | None = None
    confidence: float | None = None
    insights: list[str] = Field(default_factory=list)


class InventoryAlertSummary(BaseModel):
    total: int
    critical: int
    warning: int
    notice: int


class InventoryAlertSettingsResponse(BaseModel):
    threshold: int
    minimum_threshold: int
    maximum_threshold: int
    warning_cutoff: int
    critical_cutoff: int
    adjustment_variance_threshold: int


class InventoryAlertsResponse(BaseModel):
    settings: InventoryAlertSettingsResponse
    summary: InventoryAlertSummary
    items: list[InventoryAlertDevice]


class InventoryTotals(BaseModel):
    stores: int
    devices: int
    total_units: int
    total_value: Decimal

    @field_serializer("total_value")
    @classmethod
    def _serialize_totals_value(cls, value: Decimal) -> float:
        return float(value)


class InventoryValuation(BaseModel):
    store_id: int
    store_name: str
    device_id: int
    sku: str
    device_name: str
    categoria: str
    quantity: int
    costo_promedio_ponderado: Decimal
    valor_total_producto: Decimal
    valor_costo_producto: Decimal
    valor_total_tienda: Decimal
    valor_total_general: Decimal
    valor_costo_tienda: Decimal
    valor_costo_general: Decimal
    margen_unitario: Decimal
    margen_producto_porcentaje: Decimal
    valor_total_categoria: Decimal
    margen_categoria_valor: Decimal
    margen_categoria_porcentaje: Decimal
    margen_total_tienda: Decimal
    margen_total_general: Decimal

    @field_serializer(
        "costo_promedio_ponderado",
        "valor_total_producto",
        "valor_costo_producto",
        "valor_total_tienda",
        "valor_total_general",
        "valor_costo_tienda",
        "valor_costo_general",
        "margen_unitario",
        "valor_total_categoria",
        "margen_categoria_valor",
        "margen_total_tienda",
        "margen_total_general",
    )
    @classmethod
    def _serialize_decimal(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("margen_producto_porcentaje", "margen_categoria_porcentaje")
    @classmethod
    def _serialize_percentage(cls, value: Decimal) -> float:
        return float(value)


class MovementReportEntry(BaseModel):
    id: int
    tipo_movimiento: MovementType
    cantidad: int
    valor_total: Decimal
    sucursal_destino_id: int | None
    sucursal_destino: str | None
    sucursal_origen_id: int | None
    sucursal_origen: str | None
    comentario: str | None
    usuario: str | None
    referencia_tipo: str | None = None
    referencia_id: str | None = None
    fecha: datetime
    ultima_accion: AuditTrailInfo | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("valor_total")
    @classmethod
    def _serialize_total_value(cls, value: Decimal) -> float:
        return float(value)

    @computed_field(return_type=str | None, alias="referencia")
    def referencia_compuesta(self) -> str | None:
        if self.referencia_tipo and self.referencia_id:
            return f"{self.referencia_tipo}:{self.referencia_id}"
        if self.referencia_id:
            return self.referencia_id
        return None


class MovementTypeSummary(BaseModel):
    tipo_movimiento: MovementType
    total_cantidad: int
    total_valor: Decimal

    @field_serializer("total_valor")
    @classmethod
    def _serialize_summary_value(cls, value: Decimal) -> float:
        return float(value)


class MovementPeriodSummary(BaseModel):
    periodo: date
    tipo_movimiento: MovementType
    total_cantidad: int
    total_valor: Decimal

    @field_serializer("total_valor")
    @classmethod
    def _serialize_period_value(cls, value: Decimal) -> float:
        return float(value)


class InventoryMovementsSummary(BaseModel):
    total_movimientos: int
    total_unidades: int
    total_valor: Decimal
    por_tipo: list[MovementTypeSummary]

    @field_serializer("total_valor")
    @classmethod
    def _serialize_total_value(cls, value: Decimal) -> float:
        return float(value)


class InventoryMovementsReport(BaseModel):
    resumen: InventoryMovementsSummary
    periodos: list[MovementPeriodSummary]
    movimientos: list[MovementReportEntry]


class TopProductReportItem(BaseModel):
    device_id: int
    sku: str
    nombre: str
    store_id: int
    store_name: str
    unidades_vendidas: int
    ingresos_totales: Decimal
    margen_estimado: Decimal

    @field_serializer("ingresos_totales", "margen_estimado")
    @classmethod
    def _serialize_top_values(cls, value: Decimal) -> float:
        return float(value)


class TopProductsReport(BaseModel):
    items: list[TopProductReportItem]
    total_unidades: int
    total_ingresos: Decimal

    @field_serializer("total_ingresos")
    @classmethod
    def _serialize_total_income(cls, value: Decimal) -> float:
        return float(value)


class InventoryValueStore(BaseModel):
    store_id: int
    store_name: str
    valor_total: Decimal
    valor_costo: Decimal
    margen_total: Decimal

    @field_serializer("valor_total", "valor_costo", "margen_total")
    @classmethod
    def _serialize_value_fields(cls, value: Decimal) -> float:
        return float(value)


class InventoryValueTotals(BaseModel):
    valor_total: Decimal
    valor_costo: Decimal
    margen_total: Decimal

    @field_serializer("valor_total", "valor_costo", "margen_total")
    @classmethod
    def _serialize_totals(cls, value: Decimal) -> float:
        return float(value)


class InventoryValueReport(BaseModel):
    stores: list[InventoryValueStore]
    totals: InventoryValueTotals


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
        alias=AliasChoices("userId", "user_id"),
        description="Identificador del usuario que generó la acción",
    )
    module: str = Field(..., max_length=80,
                        description="Módulo de la interfaz donde ocurrió")
    action: str = Field(..., max_length=120,
                        description="Acción específica realizada")
    entity_id: str | None = Field(
        default=None,
        max_length=120,
        alias=AliasChoices("entityId", "entity_id"),
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


class DashboardGlobalMetrics(BaseModel):
    total_sales: float
    sales_count: int
    total_stock: int
    open_repairs: int
    gross_profit: float


class DashboardReceivableCustomer(BaseModel):
    customer_id: int
    name: str
    outstanding_debt: float
    available_credit: float | None = None


class DashboardReceivableMetrics(BaseModel):
    total_outstanding_debt: float
    customers_with_debt: int
    moroso_flagged: int
    top_debtors: list[DashboardReceivableCustomer] = Field(default_factory=list)


class DashboardChartPoint(BaseModel):
    label: str
    value: float


class InventoryMetricsResponse(BaseModel):
    totals: InventoryTotals
    top_stores: list[StoreValueMetric]
    low_stock_devices: list[LowStockDevice]
    global_performance: DashboardGlobalMetrics
    accounts_receivable: DashboardReceivableMetrics
    sales_trend: list[DashboardChartPoint] = Field(default_factory=list)
    stock_breakdown: list[DashboardChartPoint] = Field(default_factory=list)
    repair_mix: list[DashboardChartPoint] = Field(default_factory=list)
    profit_breakdown: list[DashboardChartPoint] = Field(default_factory=list)
    audit_alerts: DashboardAuditAlerts


class RotationMetric(BaseModel):
    store_id: int
    store_name: str
    device_id: int
    sku: str
    name: str
    sold_units: int
    received_units: int
    rotation_rate: float


class AnalyticsRotationResponse(BaseModel):
    items: list[RotationMetric]


class AgingMetric(BaseModel):
    device_id: int
    sku: str
    name: str
    store_id: int
    store_name: str
    days_in_stock: int
    quantity: int


class AnalyticsAgingResponse(BaseModel):
    items: list[AgingMetric]


class StockoutForecastMetric(BaseModel):
    device_id: int
    sku: str
    name: str
    store_id: int
    store_name: str
    average_daily_sales: float
    projected_days: int | None
    quantity: int
    trend: str
    trend_score: float
    confidence: float
    alert_level: str | None
    sold_units: int


class AnalyticsForecastResponse(BaseModel):
    items: list[StockoutForecastMetric]


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
    created_at: datetime
    updated_at: datetime

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


class SyncOutboxStatsEntry(BaseModel):
    entity_type: str
    priority: SyncOutboxPriority
    total: int
    pending: int
    failed: int
    latest_update: datetime | None
    oldest_pending: datetime | None


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


class StoreComparativeMetric(BaseModel):
    store_id: int
    store_name: str
    device_count: int
    total_units: int
    inventory_value: float
    average_rotation: float
    average_aging_days: float
    sales_last_30_days: float
    sales_count_last_30_days: int


class AnalyticsComparativeResponse(BaseModel):
    items: list[StoreComparativeMetric]


class ProfitMarginMetric(BaseModel):
    store_id: int
    store_name: str
    revenue: float
    cost: float
    profit: float
    margin_percent: float


class AnalyticsProfitMarginResponse(BaseModel):
    items: list[ProfitMarginMetric]


class SalesProjectionMetric(BaseModel):
    store_id: int
    store_name: str
    average_daily_units: float
    average_ticket: float
    projected_units: float
    projected_revenue: float
    confidence: float
    trend: str
    trend_score: float
    revenue_trend_score: float
    r2_revenue: float


class AnalyticsSalesProjectionResponse(BaseModel):
    items: list[SalesProjectionMetric]


class AnalyticsAlert(BaseModel):
    type: str
    level: str
    message: str
    store_id: int | None
    store_name: str
    device_id: int | None
    sku: str | None


class AnalyticsAlertsResponse(BaseModel):
    items: list[AnalyticsAlert]


class StoreRealtimeWidget(BaseModel):
    store_id: int
    store_name: str
    inventory_value: float
    sales_today: float
    last_sale_at: datetime | None
    low_stock_devices: int
    pending_repairs: int
    last_sync_at: datetime | None
    trend: str
    trend_score: float
    confidence: float


class AnalyticsRealtimeResponse(BaseModel):
    items: list[StoreRealtimeWidget]


class AnalyticsCategoriesResponse(BaseModel):
    categories: list[str]


class SyncOutboxReplayRequest(BaseModel):
    ids: list[int] = Field(..., min_length=1)


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


class GlobalReportFiltersState(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None
    module: str | None = None
    severity: SystemLogLevel | None = None

    @field_serializer("date_from", "date_to", when_used="json")
    @classmethod
    def _serialize_datetime(cls, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class GlobalReportTotals(BaseModel):
    logs: int = Field(default=0, ge=0)
    errors: int = Field(default=0, ge=0)
    info: int = Field(default=0, ge=0)
    warning: int = Field(default=0, ge=0)
    error: int = Field(default=0, ge=0)
    critical: int = Field(default=0, ge=0)
    sync_pending: int = Field(default=0, ge=0)
    sync_failed: int = Field(default=0, ge=0)
    last_activity_at: datetime | None = None

    @field_serializer("last_activity_at", when_used="json")
    @classmethod
    def _serialize_last_activity(cls, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class GlobalReportBreakdownItem(BaseModel):
    name: str
    total: int = Field(default=0, ge=0)


class GlobalReportAlert(BaseModel):
    type: Literal["critical_log", "system_error", "sync_failure"]
    level: SystemLogLevel
    message: str
    module: str | None = None
    occurred_at: datetime | None = None
    reference: str | None = None
    count: int = Field(default=1, ge=1)

    @field_serializer("occurred_at", when_used="json")
    @classmethod
    def _serialize_occurred_at(cls, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class GlobalReportOverview(BaseModel):
    generated_at: datetime
    filters: GlobalReportFiltersState
    totals: GlobalReportTotals
    module_breakdown: list[GlobalReportBreakdownItem]
    severity_breakdown: list[GlobalReportBreakdownItem]
    recent_logs: list[SystemLogEntry]
    recent_errors: list[SystemErrorEntry]
    alerts: list[GlobalReportAlert]

    @field_serializer("generated_at", when_used="json")
    @classmethod
    def _serialize_generated_at(cls, value: datetime) -> str:
        return value.isoformat()


class GlobalReportSeriesPoint(BaseModel):
    date: date
    info: int = Field(default=0, ge=0)
    warning: int = Field(default=0, ge=0)
    error: int = Field(default=0, ge=0)
    critical: int = Field(default=0, ge=0)
    system_errors: int = Field(default=0, ge=0)


class GlobalReportDashboard(BaseModel):
    generated_at: datetime
    filters: GlobalReportFiltersState
    activity_series: list[GlobalReportSeriesPoint]
    module_distribution: list[GlobalReportBreakdownItem]
    severity_distribution: list[GlobalReportBreakdownItem]

    @field_serializer("generated_at", when_used="json")
    @classmethod
    def _serialize_generated_at(cls, value: datetime) -> str:
        return value.isoformat()


# // [PACK29-*] DTOs de reportes de ventas (resumen, productos y cierre de caja)
class SalesSummaryReport(BaseModel):
    total_sales: float = Field(default=0.0, alias="totalSales")
    total_orders: int = Field(default=0, alias="totalOrders")
    avg_ticket: float = Field(default=0.0, alias="avgTicket")
    returns_count: int = Field(default=0, alias="returnsCount")
    net: float = Field(default=0.0, alias="net")

    model_config = ConfigDict(populate_by_name=True)


# // [PACK29-*] DTO para filas del top de productos vendidos
class SalesByProductItem(BaseModel):
    sku: str
    name: str
    quantity: int = Field(default=0, alias="qty", ge=0)
    gross: float = Field(default=0.0)
    net: float = Field(default=0.0)

    model_config = ConfigDict(populate_by_name=True)


# // [PACK29-*] DTO de sugerencia de cierre de caja diario
class CashCloseReport(BaseModel):
    opening: float = Field(default=0.0)
    sales_gross: float = Field(default=0.0, alias="salesGross")
    refunds: float = Field(default=0.0)
    incomes: float = Field(default=0.0)
    expenses: float = Field(default=0.0)
    closing_suggested: float = Field(default=0.0, alias="closingSuggested")

    model_config = ConfigDict(populate_by_name=True)


class AuditReminderEntry(BaseModel):
    entity_type: str
    entity_id: str
    first_seen: datetime
    last_seen: datetime
    occurrences: int = Field(..., ge=1)
    latest_action: str
    latest_details: str | None = None
    status: Literal["pending", "acknowledged"] = Field(default="pending")
    acknowledged_at: datetime | None = None
    acknowledged_by_id: int | None = None
    acknowledged_by_name: str | None = None
    acknowledged_note: str | None = None

    @field_serializer("first_seen", "last_seen", when_used="json")
    @classmethod
    def _serialize_timestamp(cls, value: datetime) -> str:
        return value.isoformat()

    @field_serializer("acknowledged_at")
    @classmethod
    def _serialize_ack(cls, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class AuditReminderSummary(BaseModel):
    threshold_minutes: int = Field(..., ge=0)
    min_occurrences: int = Field(..., ge=1)
    total: int = Field(..., ge=0)
    pending_count: int = Field(..., ge=0)
    acknowledged_count: int = Field(..., ge=0)
    persistent: list[AuditReminderEntry]


class AuditAcknowledgementCreate(BaseModel):
    entity_type: str = Field(..., min_length=1, max_length=80)
    entity_id: str = Field(..., min_length=1, max_length=80)
    note: str | None = Field(default=None, max_length=255)

    @field_validator("entity_type", "entity_id")
    @classmethod
    def _normalize_identifier(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Valor requerido")
        return normalized

    @field_validator("note")
    @classmethod
    def _normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AuditAcknowledgementResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    acknowledged_at: datetime
    acknowledged_by_id: int | None = None
    acknowledged_by_name: str | None = None
    note: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("acknowledged_at")
    @classmethod
    def _serialize_acknowledged_at(cls, value: datetime) -> str:
        return value.isoformat()


class PurchaseOrderItemCreate(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity_ordered: int = Field(..., ge=1)
    unit_cost: Decimal = Field(..., ge=Decimal("0"))

    @field_serializer("unit_cost")
    @classmethod
    def _serialize_unit_cost(cls, value: Decimal) -> float:
        return float(value)


class PurchaseOrderCreate(BaseModel):
    store_id: int = Field(..., ge=1)  # // [PACK30-31-BACKEND]
    supplier: str = Field(..., max_length=120)
    notes: str | None = Field(default=None, max_length=255)
    items: list[PurchaseOrderItemCreate]

    @model_validator(mode="before")
    @classmethod
    def _coerce_store_alias(cls, data: Any) -> Any:  # pragma: no cover - mapeo directo
        if isinstance(data, dict) and "store_id" not in data:
            for k in ("branch_id",):
                if k in data:
                    data["store_id"] = data[k]
                    break
        return data

    @field_validator("supplier")
    @classmethod
    def _validate_supplier(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Proveedor requerido")
        return normalized

    @field_validator("notes")
    @classmethod
    def _normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("items")
    @classmethod
    def _ensure_items(cls, value: list[PurchaseOrderItemCreate]) -> list[PurchaseOrderItemCreate]:
        if not value:
            raise ValueError("Debes incluir artículos en la orden de compra.")
        return value


class PurchaseOrderItemResponse(BaseModel):
    id: int
    purchase_order_id: int
    device_id: int
    quantity_ordered: int
    quantity_received: int
    unit_cost: Decimal

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("unit_cost")
    @classmethod
    def _serialize_unit_cost(cls, value: Decimal) -> float:
        return float(value)


class PurchaseReturnCreate(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)
    reason: str = Field(..., min_length=5, max_length=255)

    @field_validator("reason")
    @classmethod
    def _normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 5:
            raise ValueError("El motivo debe tener al menos 5 caracteres.")
        return normalized


class PurchaseReturnResponse(BaseModel):
    id: int
    purchase_order_id: int
    device_id: int
    quantity: int
    reason: str
    processed_by_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderResponse(BaseModel):
    id: int
    store_id: int
    supplier: str
    status: PurchaseStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
    created_by_id: int | None
    closed_at: datetime | None
    items: list[PurchaseOrderItemResponse]
    returns: list[PurchaseReturnResponse] = []

    model_config = ConfigDict(from_attributes=True)


class PurchaseReceiveItem(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)
    batch_code: str | None = Field(default=None, max_length=80)

    @field_validator("batch_code")
    @classmethod
    def _normalize_batch_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class PurchaseReceiveRequest(BaseModel):
    items: list[PurchaseReceiveItem]

    @field_validator("items")
    @classmethod
    def _ensure_items(cls, value: list[PurchaseReceiveItem]) -> list[PurchaseReceiveItem]:
        if not value:
            raise ValueError("Debes indicar artículos a recibir.")
        return value


class PurchaseImportResponse(BaseModel):
    imported: int = Field(default=0, ge=0)
    orders: list[PurchaseOrderResponse]
    errors: list[str] = Field(default_factory=list)


class PurchaseSuggestionItem(BaseModel):
    store_id: int
    store_name: str
    supplier_id: int | None
    supplier_name: str | None
    device_id: int
    sku: str
    name: str
    current_quantity: int
    minimum_stock: int
    suggested_quantity: int
    average_daily_sales: float
    projected_coverage_days: int | None
    last_30_days_sales: int
    unit_cost: Decimal = Field(default=Decimal("0"))
    reason: Literal["below_minimum", "projected_consumption"]

    @field_serializer("unit_cost")
    @classmethod
    def _serialize_unit_cost(cls, value: Decimal) -> float:
        return float(value)

    @computed_field(return_type=float)  # type: ignore[misc]
    def suggested_value(self) -> float:
        return float(self.unit_cost * Decimal(self.suggested_quantity))


class PurchaseSuggestionStore(BaseModel):
    store_id: int
    store_name: str
    total_suggested: int
    total_value: float
    items: list[PurchaseSuggestionItem]


class PurchaseSuggestionsResponse(BaseModel):
    generated_at: datetime
    lookback_days: int
    planning_horizon_days: int
    minimum_stock: int
    total_items: int
    stores: list[PurchaseSuggestionStore]


class PurchaseVendorBase(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=150)
    telefono: str | None = Field(default=None, max_length=40)
    correo: str | None = Field(default=None, max_length=120)
    direccion: str | None = Field(default=None, max_length=255)
    tipo: str | None = Field(default=None, max_length=60)
    notas: str | None = Field(default=None, max_length=255)

    @field_validator("nombre")
    @classmethod
    def _normalize_nombre(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("El nombre del proveedor es obligatorio.")
        return normalized

    @field_validator("telefono", "correo", "direccion", "tipo", "notas")
    @classmethod
    def _normalize_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class PurchaseVendorCreate(PurchaseVendorBase):
    estado: str = Field(default="activo", max_length=40)


class PurchaseVendorUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=3, max_length=150)
    telefono: str | None = Field(default=None, max_length=40)
    correo: str | None = Field(default=None, max_length=120)
    direccion: str | None = Field(default=None, max_length=255)
    tipo: str | None = Field(default=None, max_length=60)
    notas: str | None = Field(default=None, max_length=255)
    estado: str | None = Field(default=None, max_length=40)

    @field_validator("nombre", "telefono", "correo", "direccion", "tipo", "notas", "estado")
    @classmethod
    def _normalize_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class PurchaseVendorResponse(PurchaseVendorBase):
    id: int = Field(alias="id_proveedor")
    estado: str
    total_compras: Decimal = Field(default=Decimal("0"))
    total_impuesto: Decimal = Field(default=Decimal("0"))
    compras_registradas: int = Field(default=0, ge=0)
    ultima_compra: datetime | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("total_compras", "total_impuesto")
    @classmethod
    def _serialize_decimal(cls, value: Decimal) -> float:
        return float(value)


class PurchaseVendorStatusUpdate(BaseModel):
    estado: Literal["activo", "inactivo"]


class PurchaseRecordItemBase(BaseModel):
    producto_id: int = Field(..., ge=1)
    cantidad: int = Field(..., ge=1)
    costo_unitario: Decimal = Field(..., ge=Decimal("0"))

    @field_serializer("costo_unitario")
    @classmethod
    def _serialize_cost(cls, value: Decimal) -> float:
        return float(value)


class PurchaseRecordItemCreate(PurchaseRecordItemBase):
    """Detalle de ítems utilizados al registrar una compra."""


class PurchaseRecordItemResponse(PurchaseRecordItemBase):
    id: int = Field(alias="id_detalle")
    subtotal: Decimal = Field(default=Decimal("0"))
    producto_nombre: str | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("subtotal")
    @classmethod
    def _serialize_subtotal(cls, value: Decimal) -> float:
        return float(value)


class PurchaseRecordCreate(BaseModel):
    proveedor_id: int = Field(..., ge=1)
    fecha: datetime | None = None
    forma_pago: str = Field(..., max_length=60)
    estado: str = Field(default="REGISTRADA", max_length=40)
    impuesto_tasa: Decimal = Field(default=Decimal(
        "0.16"), ge=Decimal("0"), le=Decimal("1"))
    items: list[PurchaseRecordItemCreate]

    @field_validator("items")
    @classmethod
    def _ensure_items(cls, value: list[PurchaseRecordItemCreate]) -> list[PurchaseRecordItemCreate]:
        if not value:
            raise ValueError("Debes agregar productos a la compra.")
        return value


class PurchaseRecordResponse(BaseModel):
    id: int = Field(alias="id_compra")
    proveedor_id: int
    proveedor_nombre: str
    usuario_id: int
    usuario_nombre: str | None = None
    fecha: datetime
    forma_pago: str
    estado: str
    subtotal: Decimal
    impuesto: Decimal
    total: Decimal
    items: list[PurchaseRecordItemResponse]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("subtotal", "impuesto", "total")
    @classmethod
    def _serialize_amount(cls, value: Decimal) -> float:
        return float(value)


class PurchaseVendorHistory(BaseModel):
    proveedor: PurchaseVendorResponse
    compras: list[PurchaseRecordResponse]
    total: Decimal
    impuesto: Decimal
    registros: int

    @field_serializer("total", "impuesto")
    @classmethod
    def _serialize_totals(cls, value: Decimal) -> float:
        return float(value)


class PurchaseReportFilters(BaseModel):
    proveedor_id: int | None = None
    usuario_id: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    estado: str | None = None
    query: str | None = None


class PurchaseReportTotals(BaseModel):
    count: int = Field(default=0, ge=0)
    subtotal: Decimal = Field(default=Decimal("0"))
    impuesto: Decimal = Field(default=Decimal("0"))
    total: Decimal = Field(default=Decimal("0"))

    @field_serializer("subtotal", "impuesto", "total")
    @classmethod
    def _serialize_decimal(cls, value: Decimal) -> float:
        return float(value)


class PurchaseReportItem(BaseModel):
    compra_id: int
    folio: str
    proveedor_nombre: str
    usuario_nombre: str | None
    forma_pago: str
    estado: str
    subtotal: Decimal
    impuesto: Decimal
    total: Decimal
    fecha: datetime
    items: list[PurchaseRecordItemResponse]

    @field_serializer("subtotal", "impuesto", "total")
    @classmethod
    def _serialize_decimal(cls, value: Decimal) -> float:
        return float(value)


class PurchaseReport(BaseModel):
    generated_at: datetime
    filters: PurchaseReportFilters
    totals: PurchaseReportTotals
    daily_stats: list[DashboardChartPoint]
    items: list[PurchaseReportItem]


class PurchaseVendorRanking(BaseModel):
    vendor_id: int
    vendor_name: str
    total: Decimal
    orders: int

    @field_serializer("total")
    @classmethod
    def _serialize_total(cls, value: Decimal) -> float:
        return float(value)


class PurchaseUserRanking(BaseModel):
    user_id: int
    user_name: str | None
    total: Decimal
    orders: int

    @field_serializer("total")
    @classmethod
    def _serialize_total(cls, value: Decimal) -> float:
        return float(value)


class PurchaseStatistics(BaseModel):
    updated_at: datetime
    compras_registradas: int
    total: Decimal
    impuesto: Decimal
    monthly_totals: list[DashboardChartPoint]
    top_vendors: list[PurchaseVendorRanking]
    top_users: list[PurchaseUserRanking]

    @field_serializer("total", "impuesto")
    @classmethod
    def _serialize_amount(cls, value: Decimal) -> float:
        return float(value)


class RecurringOrderCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    order_type: RecurringOrderType
    payload: dict[str, Any]

    @model_validator(mode="after")
    def _validate_payload(self) -> "RecurringOrderCreate":
        if self.order_type is RecurringOrderType.PURCHASE:
            validated = PurchaseOrderCreate.model_validate(self.payload)
            self.payload = validated.model_dump()
        elif self.order_type is RecurringOrderType.TRANSFER:
            validated = TransferOrderCreate.model_validate(self.payload)
            self.payload = validated.model_dump()
        else:  # pragma: no cover - enum exhaustivo
            raise ValueError("Tipo de orden recurrente no soportado.")
        return self


class RecurringOrderResponse(BaseModel):
    id: int
    name: str
    description: str | None
    order_type: RecurringOrderType
    store_id: int | None
    store_name: str | None = None
    payload: dict[str, Any]
    created_by_id: int | None
    created_by_name: str | None = None
    last_used_by_id: int | None
    last_used_by_name: str | None = None
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None


class RecurringOrderExecutionResult(BaseModel):
    template_id: int
    order_type: RecurringOrderType
    reference_id: int
    store_id: int | None
    created_at: datetime
    summary: str


class OperationHistoryType(str, enum.Enum):
    PURCHASE = "purchase"
    TRANSFER_DISPATCH = "transfer_dispatch"
    TRANSFER_RECEIVE = "transfer_receive"
    SALE = "sale"


class OperationHistoryEntry(BaseModel):
    id: str
    operation_type: OperationHistoryType
    occurred_at: datetime
    store_id: int | None
    store_name: str | None
    technician_id: int | None
    technician_name: str | None
    reference: str | None
    description: str
    amount: Decimal | None = None

    @field_serializer("amount")
    @classmethod
    def _serialize_amount(cls, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)


class OperationHistoryTechnician(BaseModel):
    id: int
    name: str


class OperationsHistoryResponse(BaseModel):
    records: list[OperationHistoryEntry]
    technicians: list[OperationHistoryTechnician]


class ReturnRecordType(str, enum.Enum):
    PURCHASE = "purchase"
    SALE = "sale"


class ReturnRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: ReturnRecordType
    reference_id: int
    reference_label: str
    store_id: int
    store_name: str | None = None
    device_id: int
    device_name: str | None = None
    quantity: int
    reason: str
    processed_by_id: int | None = None
    processed_by_name: str | None = None
    partner_name: str | None = None
    occurred_at: datetime
    refund_amount: Decimal | None = None
    payment_method: PaymentMethod | None = None

    @field_serializer("refund_amount")
    @classmethod
    def _serialize_refund_amount(cls, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)


class ReturnsTotals(BaseModel):
    total: int
    sales: int
    purchases: int
    refunds_by_method: dict[str, Decimal] = Field(default_factory=dict)
    refund_total_amount: Decimal = Field(default=Decimal("0"))

    @field_serializer("refunds_by_method")
    @classmethod
    def _serialize_refunds(cls, value: dict[str, Decimal]) -> dict[str, float]:
        return {key: float(amount) for key, amount in value.items()}

    @field_serializer("refund_total_amount")
    @classmethod
    def _serialize_refund_total(cls, value: Decimal) -> float:
        return float(value)


class ReturnsOverview(BaseModel):
    items: list[ReturnRecord]
    totals: ReturnsTotals


class RepairOrderPartPayload(BaseModel):
    device_id: int | None = Field(default=None, ge=1)
    part_name: str | None = Field(default=None, max_length=120)
    source: RepairPartSource = Field(
        default=RepairPartSource.STOCK)  # // [PACK37-backend]
    quantity: int = Field(..., ge=1)
    unit_cost: Decimal | None = Field(default=None, ge=Decimal("0"))

    @field_validator("unit_cost")
    @classmethod
    def _normalize_unit_cost(cls, value: Decimal | None) -> Decimal:
        if value is None:
            return Decimal("0")
        return value

    @field_validator("part_name")
    @classmethod
    def _normalize_part_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class RepairOrderCreate(BaseModel):
    store_id: int = Field(..., ge=1)
    customer_id: int | None = Field(default=None, ge=1)
    customer_name: str | None = Field(default=None, max_length=120)
    customer_contact: str | None = Field(
        default=None, max_length=120)  # // [PACK37-backend]
    technician_name: str = Field(..., max_length=120)
    damage_type: str = Field(..., max_length=120)
    diagnosis: str | None = Field(
        default=None, max_length=500)  # // [PACK37-backend]
    device_model: str | None = Field(
        default=None, max_length=120)  # // [PACK37-backend]
    imei: str | None = Field(
        default=None, max_length=40)  # // [PACK37-backend]
    device_description: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=500)
    labor_cost: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    parts: list[RepairOrderPartPayload] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_repair_create_aliases(cls, data: Any) -> Any:  # pragma: no cover
        if isinstance(data, dict) and "damage_type" not in data:
            for k in ("issue",):
                if k in data:
                    data["damage_type"] = data[k]
                    break
        return data

    @field_validator(
        "customer_name",
        "customer_contact",
        "technician_name",
        "damage_type",
        "diagnosis",
        "device_model",
        "imei",
        "device_description",
        "notes",
    )
    @classmethod
    def _normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class RepairOrderUpdate(BaseModel):
    customer_id: int | None = Field(default=None, ge=1)
    customer_name: str | None = Field(default=None, max_length=120)
    customer_contact: str | None = Field(
        default=None, max_length=120)  # // [PACK37-backend]
    technician_name: str | None = Field(default=None, max_length=120)
    damage_type: str | None = Field(default=None, max_length=120)
    diagnosis: str | None = Field(
        default=None, max_length=500)  # // [PACK37-backend]
    device_model: str | None = Field(
        default=None, max_length=120)  # // [PACK37-backend]
    imei: str | None = Field(
        default=None, max_length=40)  # // [PACK37-backend]
    device_description: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=500)
    status: RepairStatus | None = None
    labor_cost: Decimal | None = Field(default=None, ge=Decimal("0"))
    parts: list[RepairOrderPartPayload] | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_repair_update_aliases(cls, data: Any) -> Any:  # pragma: no cover
        if isinstance(data, dict) and "damage_type" not in data:
            for k in ("issue",):
                if k in data:
                    data["damage_type"] = data[k]
                    break
        return data

    @field_validator(
        "customer_name",
        "customer_contact",
        "technician_name",
        "damage_type",
        "diagnosis",
        "device_model",
        "imei",
        "device_description",
        "notes",
        mode="before",
    )
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class RepairOrderPartsRequest(BaseModel):  # // [PACK37-backend]
    parts: list[RepairOrderPartPayload] = Field(default_factory=list)


class RepairOrderCloseRequest(BaseModel):  # // [PACK37-backend]
    labor_cost: Decimal | None = Field(default=None, ge=Decimal("0"))
    parts: list[RepairOrderPartPayload] | None = None


class RepairOrderPartResponse(BaseModel):
    id: int
    repair_order_id: int
    device_id: int | None
    part_name: str | None = None  # // [PACK37-backend]
    source: RepairPartSource = Field(
        default=RepairPartSource.STOCK)  # // [PACK37-backend]
    quantity: int
    unit_cost: Decimal

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("unit_cost")
    @classmethod
    def _serialize_unit_cost(cls, value: Decimal) -> float:
        return float(value)


class RepairOrderResponse(BaseModel):
    id: int
    store_id: int
    customer_id: int | None
    customer_name: str | None
    customer_contact: str | None = None  # // [PACK37-backend]
    technician_name: str
    damage_type: str
    diagnosis: str | None = None  # // [PACK37-backend]
    device_model: str | None = None  # // [PACK37-backend]
    imei: str | None = None  # // [PACK37-backend]
    device_description: str | None
    notes: str | None
    status: RepairStatus
    labor_cost: Decimal
    parts_cost: Decimal
    total_cost: Decimal
    inventory_adjusted: bool
    opened_at: datetime
    updated_at: datetime
    delivered_at: datetime | None
    parts: list[RepairOrderPartResponse]

    model_config = ConfigDict(from_attributes=True)

    @computed_field(return_type=str)  # type: ignore[misc]
    def status_color(self) -> str:
        mapping = {
            RepairStatus.PENDIENTE: "🟡",
            RepairStatus.EN_PROCESO: "🟠",
            RepairStatus.LISTO: "🟢",
            RepairStatus.ENTREGADO: "⚪",
            RepairStatus.CANCELADO: "🔴",  # // [PACK37-backend]
        }
        return mapping.get(self.status, "⬜")

    @field_serializer("labor_cost", "parts_cost", "total_cost")
    @classmethod
    def _serialize_cost(cls, value: Decimal) -> float:
        return float(value)


class SaleItemCreate(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)
    discount_percent: Decimal | None = Field(
        default=Decimal("0"), ge=Decimal("0"), le=Decimal("100")
    )
    batch_code: str | None = Field(default=None, max_length=80)
    unit_price_override: Annotated[
        Decimal | None,
        Field(
            default=None,
            ge=Decimal("0"),
            validation_alias=AliasChoices("unit_price_override", "price"),
        ),
    ]  # // [PACK34-schema]
    reservation_id: int | None = Field(default=None, ge=1)

    @field_validator("discount_percent")
    @classmethod
    def _normalize_discount(cls, value: Decimal | None) -> Decimal:
        if value is None:
            return Decimal("0")
        return value

    @field_validator("batch_code")
    @classmethod
    def _normalize_sale_batch(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class SaleCreate(BaseModel):
    store_id: int = Field(..., ge=1)  # // [PACK30-31-BACKEND]
    customer_id: int | None = Field(default=None, ge=1)
    customer_name: str | None = Field(default=None, max_length=120)
    payment_method: PaymentMethod = Field(default=PaymentMethod.EFECTIVO)
    discount_percent: Decimal | None = Field(
        default=Decimal("0"), ge=Decimal("0"), le=Decimal("100"))
    status: str = Field(default="COMPLETADA", max_length=30)
    notes: str | None = Field(default=None, max_length=255)
    items: list[SaleItemCreate]

    @model_validator(mode="before")
    @classmethod
    def _coerce_sale_aliases(cls, data: Any) -> Any:  # pragma: no cover
        if not isinstance(data, dict):
            return data
        if "store_id" not in data:
            for k in ("branch_id",):
                if k in data:
                    data["store_id"] = data[k]
                    break
        return data

    @field_validator("customer_name")
    @classmethod
    def _normalize_customer(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("notes")
    @classmethod
    def _normalize_sale_notes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("status")
    @classmethod
    def _normalize_status(cls, value: str) -> str:
        normalized = value.strip()
        return normalized or "COMPLETADA"

    @field_validator("items")
    @classmethod
    def _ensure_sale_items(cls, value: list[SaleItemCreate]) -> list[SaleItemCreate]:
        if not value:
            raise ValueError("Debes agregar artículos a la venta.")
        return value


class SaleUpdate(BaseModel):
    customer_id: int | None = Field(default=None, ge=1)
    customer_name: str | None = Field(default=None, max_length=120)
    payment_method: PaymentMethod = Field(default=PaymentMethod.EFECTIVO)
    discount_percent: Decimal | None = Field(
        default=Decimal("0"), ge=Decimal("0"), le=Decimal("100"))
    status: str = Field(default="COMPLETADA", max_length=30)
    notes: str | None = Field(default=None, max_length=255)
    items: list[SaleItemCreate]

    @field_validator("customer_name")
    @classmethod
    def _normalize_update_customer(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("notes")
    @classmethod
    def _normalize_update_notes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("status")
    @classmethod
    def _normalize_update_status(cls, value: str) -> str:
        normalized = value.strip()
        return normalized or "COMPLETADA"

    @field_validator("items")
    @classmethod
    def _ensure_update_items(cls, value: list[SaleItemCreate]) -> list[SaleItemCreate]:
        if not value:
            raise ValueError("Debes agregar artículos a la venta.")
        return value


class SaleStoreSummary(BaseModel):
    id: int
    name: str
    location: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SaleUserSummary(BaseModel):
    id: int
    username: str
    full_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SaleDeviceSummary(BaseModel):
    id: int
    sku: str
    name: str
    modelo: str | None = None
    imei: str | None = None
    serial: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SaleItemResponse(BaseModel):
    id: int
    sale_id: int
    device_id: int
    quantity: int
    unit_price: Decimal
    discount_amount: Decimal
    total_line: Decimal
    device: SaleDeviceSummary | None = None
    reservation_id: int | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("unit_price", "discount_amount", "total_line")
    @classmethod
    def _serialize_amount(cls, value: Decimal) -> float:
        return float(value)


class SaleCustomerSummary(BaseModel):
    id: int
    name: str
    outstanding_debt: Decimal

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("outstanding_debt")
    @classmethod
    def _serialize_debt(cls, value: Decimal) -> float:
        return float(value)


class CashSessionSummary(BaseModel):
    id: int
    status: CashSessionStatus
    opened_at: datetime
    closed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SaleResponse(BaseModel):
    id: int
    store_id: int
    customer_id: int | None
    customer_name: str | None
    payment_method: PaymentMethod
    discount_percent: Decimal
    subtotal_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    status: str
    notes: str | None
    created_at: datetime
    performed_by_id: int | None
    cash_session_id: int | None
    customer: SaleCustomerSummary | None = None
    cash_session: CashSessionSummary | None = None
    items: list[SaleItemResponse]
    returns: list["SaleReturnResponse"] = []
    store: SaleStoreSummary | None = None
    performed_by: SaleUserSummary | None = None
    ultima_accion: AuditTrailInfo | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("discount_percent", "subtotal_amount", "tax_amount", "total_amount")
    @classmethod
    def _serialize_sale_amount(cls, value: Decimal) -> float:
        return float(value)

    @computed_field(alias="fecha", return_type=datetime)
    def fecha_operacion(self) -> datetime:
        return self.created_at


class SaleReturnItem(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)
    reason: str = Field(..., min_length=5, max_length=255)

    @field_validator("reason")
    @classmethod
    def _normalize_sale_reason(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 5:
            raise ValueError("El motivo debe tener al menos 5 caracteres.")
        return normalized


class SaleReturnCreate(BaseModel):
    sale_id: int = Field(..., ge=1)
    items: list[SaleReturnItem]

    @field_validator("items")
    @classmethod
    def _ensure_return_items(cls, value: list[SaleReturnItem]) -> list[SaleReturnItem]:
        if not value:
            raise ValueError("Debes indicar artículos a devolver.")
        return value


class SaleReturnResponse(BaseModel):
    id: int
    sale_id: int
    device_id: int
    quantity: int
    reason: str
    processed_by_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field(alias="fecha", return_type=datetime)
    def fecha_registro(self) -> datetime:
        return self.created_at


class SaleHistorySearchResponse(BaseModel):
    by_ticket: list[SaleResponse] = Field(default_factory=list)
    by_date: list[SaleResponse] = Field(default_factory=list)
    by_customer: list[SaleResponse] = Field(default_factory=list)
    by_qr: list[SaleResponse] = Field(default_factory=list)


class SalesReportFilters(BaseModel):
    store_id: int | None = None
    customer_id: int | None = None
    performed_by_id: int | None = None
    product_id: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    query: str | None = None


class SalesReportTotals(BaseModel):
    count: int
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    cost: Decimal = Decimal("0")
    net_income: Decimal = Decimal("0")
    daily_average: Decimal = Decimal("0")

    @field_serializer("subtotal", "tax", "total", "cost", "net_income", "daily_average")
    @classmethod
    def _serialize_totals(cls, value: Decimal) -> float:
        return float(value)


class SalesReportItem(BaseModel):
    sale_id: int
    folio: str
    store_name: str
    customer_name: str | None
    performed_by: str | None
    payment_method: PaymentMethod
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    created_at: datetime
    items: list[SaleItemResponse]
    ultima_accion: AuditTrailInfo | None = None

    @field_serializer("subtotal", "tax", "total")
    @classmethod
    def _serialize_amount(cls, value: Decimal) -> float:
        return float(value)


class SalesReportGroup(BaseModel):
    id: int | None
    name: str
    total: Decimal
    count: int

    @field_serializer("total")
    @classmethod
    def _serialize_total(cls, value: Decimal) -> float:
        return float(value)


class SalesReportProduct(BaseModel):
    product_id: int
    sku: str | None
    name: str
    units: int
    total: Decimal

    @field_serializer("total")
    @classmethod
    def _serialize_total(cls, value: Decimal) -> float:
        return float(value)


class SalesReport(BaseModel):
    generated_at: datetime
    filters: SalesReportFilters
    totals: SalesReportTotals
    daily_stats: list[DashboardChartPoint]
    items: list[SalesReportItem]
    by_store: list[SalesReportGroup] = Field(default_factory=list)
    by_user: list[SalesReportGroup] = Field(default_factory=list)
    top_products: list[SalesReportProduct] = Field(default_factory=list)


class POSCartItem(BaseModel):
    """Elemento del carrito POS aceptando identificadores flexibles."""

    # // [PACK34-schema]
    device_id: int | None = Field(default=None, ge=1)
    imei: str | None = Field(default=None, max_length=18)
    quantity: int = Field(..., ge=1)
    discount_percent: Decimal | None = Field(
        default=Decimal("0"), ge=Decimal("0"), le=Decimal("100"))
    unit_price_override: Decimal | None = Field(default=None, ge=Decimal("0"))
    tax_code: str | None = Field(default=None, max_length=50)
    reservation_id: int | None = Field(default=None, ge=1)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("discount_percent")
    @classmethod
    def _normalize_pos_discount(cls, value: Decimal | None) -> Decimal:
        if value is None:
            return Decimal("0")
        return value

    @model_validator(mode="before")
    @classmethod
    def _coerce_cart_aliases(cls, data: Any) -> Any:  # pragma: no cover
        if not isinstance(data, dict):
            return data
        mapping = {
            "device_id": ["productId", "product_id"],
            "imei": ["imei_1", "imei1"],
            "quantity": ["qty"],
            "discount_percent": ["discount"],
            "unit_price_override": ["price"],
            "tax_code": ["taxCode"],
        }
        for target, sources in mapping.items():
            if target not in data:
                for s in sources:
                    if s in data:
                        data[target] = data[s]
                        break
        return data


class POSSalePaymentInput(BaseModel):
    """Definición de pago para registrar montos por método."""

    # // [PACK34-schema]
    method: PaymentMethod
    amount: Decimal = Field(..., ge=Decimal("0"))
    reference: str | None = Field(default=None, max_length=64)
    terminal_id: str | None = Field(default=None, max_length=40, alias="terminalId")
    tip_amount: Decimal | None = Field(default=None, ge=Decimal("0"), alias="tipAmount")
    token: str | None = Field(default=None, max_length=128)
    metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _coerce_method_alias(cls, data: Any) -> Any:  # pragma: no cover
        if isinstance(data, dict) and "method" not in data:
            for k in ("paymentMethod",):
                if k in data:
                    data["method"] = data[k]
                    break
        return data

    @field_validator("reference", "terminal_id", "token")
    @classmethod
    def _normalize_optional_str(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("metadata", mode="before")
    @classmethod
    def _ensure_metadata(cls, value: Any) -> dict[str, str]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return {str(k): str(v) for k, v in value.items()}
        raise ValueError("metadata debe ser un diccionario de texto")


class POSSaleRequest(BaseModel):
    store_id: int = Field(..., ge=1)
    customer_id: int | None = Field(default=None, ge=1)
    customer_name: str | None = Field(default=None, max_length=120)
    payment_method: PaymentMethod = Field(default=PaymentMethod.EFECTIVO)
    discount_percent: Decimal | None = Field(
        default=Decimal("0"), ge=Decimal("0"), le=Decimal("100")
    )
    notes: str | None = Field(default=None, max_length=255)
    items: list[POSCartItem]
    draft_id: int | None = Field(default=None, ge=1)
    save_as_draft: bool = Field(default=False)
    confirm: bool = Field(default=False)
    apply_taxes: bool = Field(default=True)
    coupons: list[str] = Field(default_factory=list)
    cash_session_id: int | None = Field(default=None, ge=1)
    payment_breakdown: dict[str, Decimal] = Field(default_factory=dict)
    payments: list[POSSalePaymentInput] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("customer_name")
    @classmethod
    def _normalize_pos_customer(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("notes")
    @classmethod
    def _normalize_pos_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("items")
    @classmethod
    def _ensure_pos_items(cls, value: list[POSCartItem]) -> list[POSCartItem]:
        if not value:
            raise ValueError("Debes agregar dispositivos al carrito.")
        return value

    @field_validator("payment_breakdown", mode="before")
    @classmethod
    def _normalize_breakdown(cls, value: dict[str, Decimal] | None) -> dict[str, Decimal]:
        if value is None:
            return {}
        normalized: dict[str, Decimal] = {}
        for method_key, amount in value.items():
            method = method_key.strip().upper()
            try:
                PaymentMethod(method)
            except ValueError as exc:  # pragma: no cover - validation error path
                raise ValueError(
                    "Método de pago inválido en el desglose.") from exc
            normalized[method] = Decimal(str(amount))
        return normalized

    @field_validator("coupons")
    @classmethod
    def _normalize_coupons(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in value:
            trimmed = (raw or "").strip()
            if len(trimmed) < 3:
                continue
            code = trimmed.upper()
            if code in seen:
                continue
            seen.add(code)
            normalized.append(code)
        return normalized

    @model_validator(mode="before")
    @classmethod
    def _coerce_pos_aliases(cls, data: Any) -> Any:  # pragma: no cover
        if not isinstance(data, dict):
            return data
        mapping = {
            "store_id": ["branchId", "branch_id"],
            "customer_name": ["customer"],
            "payment_method": ["payment_method", "defaultPaymentMethod"],
            "notes": ["note", "notes"],
            "cash_session_id": ["sessionId"],
        }
        for target, sources in mapping.items():
            if target not in data:
                for s in sources:
                    if s in data:
                        data[target] = data[s]
                        break
        return data

    @model_validator(mode="after")
    def _sync_pos_payments(self) -> "POSSaleRequest":
        # // [PACK34-schema]
        if self.payments:
            breakdown: dict[str, Decimal] = {}
            for payment in self.payments:
                method_key = payment.method.value
                total_amount = Decimal(str(payment.amount))
                if payment.tip_amount is not None:
                    total_amount += Decimal(str(payment.tip_amount))
                breakdown[method_key] = (
                    breakdown.get(method_key, Decimal("0")) + total_amount
                )
            self.payment_breakdown = breakdown
        return self


class POSDraftResponse(BaseModel):
    id: int
    store_id: int
    payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class POSSaleResponse(BaseModel):
    status: Literal["draft", "registered"]
    sale: SaleResponse | None = None
    draft: POSDraftResponse | None = None
    receipt_url: str | None = None
    warnings: list[str] = Field(default_factory=list)
    cash_session_id: int | None = None
    payment_breakdown: dict[str, float] = Field(default_factory=dict)
    receipt_pdf_base64: str | None = Field(default=None)
    applied_promotions: list[POSAppliedPromotion] = Field(default_factory=list)
    debt_summary: CustomerDebtSnapshot | None = None
    credit_schedule: list[CreditScheduleEntry] = Field(default_factory=list)
    debt_receipt_pdf_base64: str | None = None
    payment_receipts: list[CustomerPaymentReceiptResponse] = Field(
        default_factory=list
    )
    electronic_payments: list["POSElectronicPaymentResult"] = Field(default_factory=list)

    @field_serializer("payment_breakdown")
    @classmethod
    def _serialize_breakdown(cls, value: dict[str, float]) -> dict[str, float]:
        return {key: float(amount) for key, amount in value.items()}

    @computed_field(return_type=float)  # type: ignore[misc]
    def total_caja(self) -> float:
        if self.sale is not None:
            return float(self.sale.total_amount)
        if self.payment_breakdown:
            return float(sum(self.payment_breakdown.values()))
        return 0.0


class POSReceiptDeliveryChannel(str, enum.Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
class POSElectronicPaymentResult(BaseModel):
    terminal_id: str
    method: PaymentMethod
    transaction_id: str
    status: str
    approval_code: str | None = None
    reconciled: bool = Field(default=False)
    tip_amount: Decimal | None = None

    @field_serializer("tip_amount")
    @classmethod
    def _serialize_tip(cls, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)


class POSReturnItemRequest(BaseModel):
    """Item devuelto desde el POS identificable por producto o IMEI."""


class POSReceiptDeliveryRequest(BaseModel):
    channel: POSReceiptDeliveryChannel
    recipient: str = Field(..., min_length=5, max_length=255)
    message: str | None = Field(default=None, max_length=500)
    subject: str | None = Field(default=None, max_length=120)

    @field_validator("recipient")
    @classmethod
    def _normalize_recipient(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("recipient_required")
        return normalized


class POSReceiptDeliveryResponse(BaseModel):
    channel: POSReceiptDeliveryChannel
    status: str


class POSReturnRequest(BaseModel):
    """Solicitud de devolución rápida en POS (alias normalizados)."""

    original_sale_id: int = Field(..., ge=1)
    items: list[POSReturnItemRequest]
    reason: str | None = Field(default=None, max_length=255)

    @model_validator(mode="before")
    @classmethod
    def _coerce_return_aliases(cls, data: Any) -> Any:  # pragma: no cover
        if isinstance(data, dict) and "original_sale_id" not in data:
            for k in ("originalSaleId", "sale_id"):
                if k in data:
                    data["original_sale_id"] = data[k]
                    break
        return data

    @field_validator("items")
    @classmethod
    def _ensure_return_items(cls, value: list[POSReturnItemRequest]) -> list[POSReturnItemRequest]:
        if not value:
            raise ValueError("Debes indicar artículos a devolver.")
        return value

    @field_validator("reason")
    @classmethod
    def _normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class POSReturnResponse(BaseModel):
    """Respuesta estandarizada tras registrar devoluciones POS."""

    # // [PACK34-schema]
    sale_id: int
    return_ids: list[int]
    notes: str | None = None


class POSSaleDetailResponse(BaseModel):
    """Detalle completo de ventas POS con acceso a recibo."""

    # // [PACK34-schema]
    sale: SaleResponse
    receipt_url: str
    receipt_pdf_base64: str | None = None
    debt_summary: CustomerDebtSnapshot | None = None
    credit_schedule: list[CreditScheduleEntry] = Field(default_factory=list)


class CashDenominationInput(BaseModel):
    value: Decimal = Field(..., gt=Decimal("0"))
    quantity: int = Field(default=0, ge=0)

    @field_serializer("value")
    @classmethod
    def _serialize_value(cls, value: Decimal) -> float:
        return float(value)


class CashRegisterEntryBase(BaseModel):
    session_id: int = Field(..., ge=1)
    entry_type: CashEntryType
    amount: Decimal = Field(..., gt=Decimal("0"))
    reason: str = Field(..., min_length=5, max_length=255)
    notes: str | None = Field(default=None, max_length=255)

    @field_validator("reason")
    @classmethod
    def _normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 5:
            raise ValueError("El motivo debe tener al menos 5 caracteres.")
        return normalized

    @field_validator("notes")
    @classmethod
    def _normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CashRegisterEntryCreate(CashRegisterEntryBase):
    pass


class CashRegisterEntryResponse(CashRegisterEntryBase):
    id: int
    created_by_id: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("amount")
    @classmethod
    def _serialize_amount(cls, value: Decimal) -> float:
        return float(value)


class CashSessionOpenRequest(BaseModel):
    store_id: int = Field(..., ge=1)
    opening_amount: Decimal = Field(..., ge=Decimal("0"))
    notes: str | None = Field(default=None, max_length=255)

    @field_validator("notes")
    @classmethod
    def _normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CashSessionCloseRequest(BaseModel):
    session_id: int = Field(..., ge=1)
    closing_amount: Decimal = Field(..., ge=Decimal("0"))
    notes: str | None = Field(default=None, max_length=255)
    payment_breakdown: dict[str, Decimal] = Field(default_factory=dict)
    denominations: list["CashDenominationInput"] = Field(default_factory=list)
    reconciliation_notes: str | None = Field(default=None, max_length=255)
    difference_reason: str | None = Field(default=None, max_length=255)

    @field_validator("notes")
    @classmethod
    def _normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("payment_breakdown", mode="before")
    @classmethod
    def _normalize_breakdown(cls, value: dict[str, Decimal] | None) -> dict[str, Decimal]:
        if value is None:
            return {}
        normalized: dict[str, Decimal] = {}
        for method_key, amount in value.items():
            method = method_key.strip().upper()
            try:
                PaymentMethod(method)
            except ValueError as exc:
                raise ValueError("Método de pago inválido.") from exc
            normalized[method] = Decimal(str(amount))
        return normalized

    @field_validator("reconciliation_notes", "difference_reason")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CashSessionResponse(BaseModel):
    id: int
    store_id: int
    status: CashSessionStatus
    opening_amount: Decimal
    closing_amount: Decimal
    expected_amount: Decimal
    difference_amount: Decimal
    payment_breakdown: dict[str, float]
    denomination_breakdown: dict[str, int]
    reconciliation_notes: str | None
    difference_reason: str | None
    notes: str | None
    opened_by_id: int | None
    closed_by_id: int | None
    opened_at: datetime
    closed_at: datetime | None
    entries: list["CashRegisterEntryResponse"] | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer(
        "opening_amount",
        "closing_amount",
        "expected_amount",
        "difference_amount",
    )
    @classmethod
    def _serialize_amount(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("payment_breakdown")
    @classmethod
    def _serialize_breakdown(cls, value: dict[str, float]) -> dict[str, float]:
        return {key: float(amount) for key, amount in value.items()}

    @field_serializer("denomination_breakdown")
    @classmethod
    def _serialize_denominations(cls, value: dict[str, int]) -> dict[str, int]:
        return {str(denomination): int(count) for denomination, count in value.items()}


class POSSessionOpenPayload(BaseModel):
    """Carga útil para aperturas de caja rápidas desde POS (branch/store alias)."""

    branch_id: int = Field(..., ge=1)
    opening_amount: Decimal = Field(..., ge=Decimal("0"))
    notes: str | None = Field(default=None, max_length=255)

    @model_validator(mode="before")
    @classmethod
    def _coerce_open_aliases(cls, data: Any) -> Any:  # pragma: no cover
        if isinstance(data, dict) and "branch_id" not in data:
            for k in ("branchId", "store_id"):
                if k in data:
                    data["branch_id"] = data[k]
                    break
        return data

    @field_validator("notes")
    @classmethod
    def _normalize_pos_session_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class POSSessionClosePayload(BaseModel):
    """Datos requeridos para cerrar sesiones POS."""

    # // [PACK34-schema]
    session_id: int = Field(..., ge=1)
    closing_amount: Decimal = Field(..., ge=Decimal("0"))
    notes: str | None = Field(default=None, max_length=255)
    payments: dict[str, Decimal] = Field(default_factory=dict)

    @field_validator("notes")
    @classmethod
    def _normalize_close_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("payments", mode="before")
    @classmethod
    def _normalize_payments(
        cls, value: dict[str, Decimal] | list[dict[str, Decimal | str]] | None
    ) -> dict[str, Decimal]:
        normalized: dict[str, Decimal] = {}
        if value is None:
            return normalized
        if isinstance(value, dict):
            source = value.items()
        else:
            source = []
            for entry in value:
                method = str(entry.get("method") or entry.get(
                    "paymentMethod") or "").strip()
                amount = entry.get("amount") or entry.get("value")
                if not method:
                    continue
                source.append((method, amount))
        for raw_method, raw_amount in source:
            method_key = str(raw_method).strip().upper()
            try:
                PaymentMethod(method_key)
            except ValueError as exc:
                raise ValueError("Método de pago inválido.") from exc
            normalized[method_key] = Decimal(str(raw_amount))
        return normalized


class POSSessionSummary(BaseModel):
    """Resumen compacto de sesiones POS para la UI."""

    # // [PACK34-schema]
    session_id: int
    branch_id: int
    status: CashSessionStatus
    opened_at: datetime
    closing_at: datetime | None = None
    opening_amount: Decimal | None = None
    closing_amount: Decimal | None = None
    expected_amount: Decimal | None = None
    difference_amount: Decimal | None = None
    payment_breakdown: dict[str, float] = Field(default_factory=dict)
    denomination_breakdown: dict[str, int] = Field(default_factory=dict)
    reconciliation_notes: str | None = None
    difference_reason: str | None = None

    @classmethod
    def from_model(cls, session: "models.CashRegisterSession") -> "POSSessionSummary":
        from .. import models  # Importación tardía para evitar ciclos

        # // [PACK34-schema]
        return cls(
            session_id=session.id,
            branch_id=session.store_id,
            status=session.status,
            opened_at=session.opened_at,
            closing_at=session.closed_at,
            opening_amount=getattr(session, "opening_amount", None),
            closing_amount=getattr(session, "closing_amount", None),
            expected_amount=getattr(session, "expected_amount", None),
            difference_amount=getattr(session, "difference_amount", None),
            payment_breakdown={
                key: float(value) for key, value in (session.payment_breakdown or {}).items()
            },
            denomination_breakdown={
                str(key): int(count)
                for key, count in (session.denomination_breakdown or {}).items()
            },
            reconciliation_notes=getattr(session, "reconciliation_notes", None),
            difference_reason=getattr(session, "difference_reason", None),
        )

    @field_serializer(
        "opening_amount",
        "closing_amount",
        "expected_amount",
        "difference_amount",
    )
    @classmethod
    def _serialize_optional_amount(cls, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)

    @field_serializer("denomination_breakdown")
    @classmethod
    def _serialize_optional_denominations(cls, value: dict[str, int]) -> dict[str, int]:
        return {str(denomination): int(count) for denomination, count in value.items()}


class POSTaxInfo(BaseModel):
    """Catálogo simple de impuestos POS."""

    # // [PACK34-schema]
    code: str
    name: str
    rate: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))

    @field_serializer("rate")
    @classmethod
    def _serialize_tax_rate(cls, value: Decimal) -> float:
        return float(value)


class POSConnectorType(str, enum.Enum):
    """Tipos de conectores de hardware permitidos."""

    USB = "usb"
    NETWORK = "network"


class POSPrinterMode(str, enum.Enum):
    """Tipos de impresoras POS disponibles."""

    THERMAL = "thermal"
    FISCAL = "fiscal"


class POSConnectorSettings(BaseModel):
    """Configura el punto de conexión del dispositivo POS."""

    type: POSConnectorType = Field(default=POSConnectorType.USB)
    identifier: str = Field(default="predeterminado", max_length=120)
    path: str | None = Field(default=None, max_length=255)
    host: str | None = Field(default=None, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)

    @model_validator(mode="after")
    def _validate_target(self) -> "POSConnectorSettings":
        if self.type is POSConnectorType.NETWORK:
            if not self.host:
                raise ValueError("Los conectores de red requieren host configurado.")
        return self


class POSPrinterSettings(BaseModel):
    """Describe impresoras térmicas o fiscales."""

    name: str = Field(..., max_length=120)
    mode: POSPrinterMode = Field(default=POSPrinterMode.THERMAL)
    connector: POSConnectorSettings = Field(default_factory=POSConnectorSettings)
    paper_width_mm: int | None = Field(default=None, ge=40, le=120)
    is_default: bool = Field(default=False)
    vendor: str | None = Field(default=None, max_length=80)
    supports_qr: bool = Field(default=False)


class POSCashDrawerSettings(BaseModel):
    """Define la gaveta de efectivo conectada al POS."""

    enabled: bool = Field(default=False)
    connector: POSConnectorSettings | None = Field(default=None)
    auto_open_on_cash_sale: bool = Field(default=True)
    pulse_duration_ms: int = Field(default=150, ge=50, le=500)


class POSCustomerDisplaySettings(BaseModel):
    """Configura la pantalla de cliente enlazada al POS."""

    enabled: bool = Field(default=False)
    channel: Literal["websocket", "local"] = Field(default="websocket")
    brightness: int = Field(default=100, ge=10, le=100)
    theme: Literal["dark", "light"] = Field(default="dark")
    message_template: str | None = Field(default=None, max_length=160)


class POSHardwareSettings(BaseModel):
    """Agrupa la configuración de hardware POS por sucursal."""

    printers: list[POSPrinterSettings] = Field(default_factory=list)
    cash_drawer: POSCashDrawerSettings = Field(default_factory=POSCashDrawerSettings)
    customer_display: POSCustomerDisplaySettings = Field(
        default_factory=POSCustomerDisplaySettings
    )
class POSTerminalConfig(BaseModel):
    id: str
    label: str
    adapter: str
    currency: str

    @field_validator("id", "label", "adapter", "currency")
    @classmethod
    def _normalize_terminal_str(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Los campos de terminal no pueden estar vacíos")
        return normalized


class POSConfigResponse(BaseModel):
    store_id: int
    tax_rate: Decimal
    invoice_prefix: str
    printer_name: str | None
    printer_profile: str | None
    quick_product_ids: list[int]
    hardware_settings: POSHardwareSettings = Field(
        default_factory=POSHardwareSettings
    )
    updated_at: datetime
    terminals: list[POSTerminalConfig] = Field(default_factory=list)
    tip_suggestions: list[float] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("tax_rate")
    @classmethod
    def _serialize_tax(cls, value: Decimal) -> float:
        return float(value)

    @classmethod
    def from_model(
        cls,
        config: "models.POSConfig",
        *,
        terminals: dict[str, dict[str, Any]],
        tip_suggestions: list[Decimal],
    ) -> "POSConfigResponse":
        from .. import models  # Importación tardía para evitar ciclos

        terminals_payload = [
            POSTerminalConfig(
                id=terminal_id,
                label=str(data.get("label") or terminal_id),
                adapter=str(data.get("adapter") or "").strip() or "banco_atlantida",
                currency=str(data.get("currency") or "HNL"),
            )
            for terminal_id, data in terminals.items()
        ]
        return cls(
            store_id=config.store_id,
            tax_rate=config.tax_rate,
            invoice_prefix=config.invoice_prefix,
            printer_name=config.printer_name,
            printer_profile=config.printer_profile,
            quick_product_ids=list(config.quick_product_ids or []),
            updated_at=config.updated_at,
            terminals=terminals_payload,
            tip_suggestions=[float(Decimal(str(value))) for value in tip_suggestions],
        )


class POSPromotionFeatureFlags(BaseModel):
    volume: bool = False
    combos: bool = False
    coupons: bool = False


class POSVolumePromotion(BaseModel):
    id: str = Field(..., min_length=1, max_length=60)
    device_id: int = Field(..., ge=1)
    min_quantity: int = Field(..., ge=1)
    discount_percent: Decimal = Field(..., gt=Decimal("0"), le=Decimal("100"))

    @field_serializer("discount_percent")
    @classmethod
    def _serialize_discount(cls, value: Decimal) -> float:
        return float(value)


class POSComboPromotionItem(BaseModel):
    device_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)


class POSComboPromotion(BaseModel):
    id: str = Field(..., min_length=1, max_length=60)
    items: list[POSComboPromotionItem] = Field(default_factory=list)
    discount_percent: Decimal = Field(..., gt=Decimal("0"), le=Decimal("100"))

    @field_serializer("discount_percent")
    @classmethod
    def _serialize_discount(cls, value: Decimal) -> float:
        return float(value)

    @field_validator("items")
    @classmethod
    def _ensure_items(cls, value: list[POSComboPromotionItem]) -> list[POSComboPromotionItem]:
        if not value:
            raise ValueError("Los combos deben incluir al menos un artículo.")
        return value


class POSCouponPromotion(BaseModel):
    code: str = Field(..., min_length=3, max_length=40)
    discount_percent: Decimal = Field(..., gt=Decimal("0"), le=Decimal("100"))
    description: str | None = Field(default=None, max_length=120)

    @field_serializer("discount_percent")
    @classmethod
    def _serialize_discount(cls, value: Decimal) -> float:
        return float(value)


class POSPromotionsConfig(BaseModel):
    feature_flags: POSPromotionFeatureFlags = Field(default_factory=POSPromotionFeatureFlags)
    volume_promotions: list[POSVolumePromotion] = Field(default_factory=list)
    combo_promotions: list[POSComboPromotion] = Field(default_factory=list)
    coupons: list[POSCouponPromotion] = Field(default_factory=list)


class POSPromotionsUpdate(POSPromotionsConfig):
    store_id: int = Field(..., ge=1)


class POSPromotionsResponse(POSPromotionsConfig):
    store_id: int
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class POSAppliedPromotion(BaseModel):
    id: str
    promotion_type: Literal["volume", "combo", "coupon"]
    description: str
    discount_percent: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), le=Decimal("100"))
    discount_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    affected_items: list[int] = Field(default_factory=list)
    coupon_code: str | None = Field(default=None, max_length=60)

    @field_serializer("discount_percent", "discount_amount")
    @classmethod
    def _serialize_amount(cls, value: Decimal) -> float:
        return float(value)


class POSConfigUpdate(BaseModel):
    store_id: int = Field(..., ge=1)
    tax_rate: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))
    invoice_prefix: str = Field(..., min_length=1, max_length=12)
    printer_name: str | None = Field(default=None, max_length=120)
    printer_profile: str | None = Field(default=None, max_length=255)
    quick_product_ids: list[int] = Field(default_factory=list)
    hardware_settings: POSHardwareSettings | None = Field(default=None)

    @field_validator("quick_product_ids")
    @classmethod
    def _validate_quick_products(cls, value: list[int]) -> list[int]:
        normalized = []
        for item in value:
            if int(item) < 1:
                raise ValueError(
                    "Los identificadores rápidos deben ser positivos.")
            normalized.append(int(item))
        return normalized


class POSHardwarePrintTestRequest(BaseModel):
    """Solicitud de impresión de prueba."""

    store_id: int = Field(..., ge=1)
    printer_name: str | None = Field(default=None, max_length=120)
    mode: POSPrinterMode = Field(default=POSPrinterMode.THERMAL)
    sample: str = Field(default="*** PRUEBA DE IMPRESIÓN POS ***", max_length=512)


class POSHardwareDrawerOpenRequest(BaseModel):
    """Solicitud para apertura de gaveta."""

    store_id: int = Field(..., ge=1)
    connector_identifier: str | None = Field(default=None, max_length=120)
    pulse_duration_ms: int | None = Field(default=None, ge=50, le=500)


class POSHardwareDisplayPushRequest(BaseModel):
    """Eventos a mostrar en la pantalla de cliente."""

    store_id: int = Field(..., ge=1)
    headline: str = Field(..., max_length=80)
    message: str | None = Field(default=None, max_length=240)
    total_amount: float | None = Field(default=None, ge=0)


class POSHardwareActionResponse(BaseModel):
    """Respuesta estandarizada para acciones de hardware."""

    status: Literal["queued", "ok", "error"] = Field(default="queued")
    message: str = Field(default="")
    details: dict[str, Any] | None = Field(default=None)


class BackupRunRequest(BaseModel):
    nota: str | None = Field(default=None, max_length=255)
    componentes: set[BackupComponent] | None = Field(
        default=None,
        description=(
            "Componentes específicos a incluir en el respaldo. Si se omite se respaldan todos."
        ),
    )


class BackupJobResponse(BaseModel):
    id: int
    mode: BackupMode
    executed_at: datetime
    pdf_path: str
    archive_path: str
    json_path: str
    sql_path: str
    config_path: str
    metadata_path: str
    critical_directory: str
    components: list[BackupComponent]
    total_size_bytes: int
    notes: str | None
    triggered_by_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BackupRestoreRequest(BaseModel):
    componentes: set[BackupComponent] | None = Field(
        default=None,
        description="Componentes a restaurar. Si no se especifica se usarán todos los disponibles.",
    )
    destino: str | None = Field(
        default=None,
        max_length=255,
        description="Directorio destino para los archivos restaurados. Se crea si no existe.",
    )
    aplicar_base_datos: bool = Field(
        default=False,
        description=(
            "Cuando es verdadero ejecuta el volcado SQL directamente sobre la base de datos activa."
        ),
    )


class BackupRestoreResponse(BaseModel):
    job_id: int
    componentes: list[BackupComponent]
    destino: str | None
    resultados: dict[str, str]


class ReleaseInfo(BaseModel):
    version: str = Field(..., description="Versión disponible del producto")
    release_date: date = Field(..., description="Fecha oficial de liberación")
    notes: str = Field(..., description="Resumen de cambios relevantes")
    download_url: str = Field(...,
                              description="Enlace de descarga del instalador")


class UpdateStatus(BaseModel):
    current_version: str
    latest_version: str | None
    is_update_available: bool
    latest_release: ReleaseInfo | None = None


class IntegrationCredentialInfo(BaseModel):
    """Resumen de credenciales expuestas a los administradores."""

    token_hint: str = Field(
        ...,
        min_length=4,
        max_length=8,
        description="Últimos caracteres visibles del token activo.",
    )
    rotated_at: datetime = Field(
        ...,
        description="Marca temporal en UTC de la última rotación del token.",
    )
    expires_at: datetime = Field(
        ...,
        description="Fecha en UTC en la que expira el token vigente.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token_hint": "a1B3",
                "rotated_at": "2025-11-06T04:00:00+00:00",
                "expires_at": "2026-02-04T04:00:00+00:00",
            }
        }
    )


class IntegrationHealthStatus(BaseModel):
    """Estado de salud reportado por los monitores corporativos."""

    status: str = Field(
        ...,
        min_length=2,
        max_length=40,
        description="Estado declarado (por ejemplo: operational, degraded, offline).",
    )
    checked_at: datetime | None = Field(
        default=None,
        description="Marca temporal en UTC del último chequeo exitoso.",
    )
    message: str | None = Field(
        default=None,
        max_length=200,
        description="Mensaje opcional con detalles del monitoreo.",
    )


class IntegrationProviderSummary(BaseModel):
    """Información general visible en el catálogo de integraciones."""

    slug: str = Field(
        ...,
        min_length=3,
        max_length=60,
        description="Identificador corto de la integración.",
    )
    name: str = Field(
        ...,
        min_length=3,
        max_length=120,
        description="Nombre comercial del conector externo.",
    )
    category: str = Field(
        ...,
        min_length=3,
        max_length=60,
        description="Categoría operativa del conector (analítica, automatización, etc.).",
    )
    status: str = Field(
        ...,
        min_length=2,
        max_length=40,
        description="Estado corporativo actual (active, beta, deprecated, etc.).",
    )
    supports_push: bool = Field(
        default=False,
        description="Indica si Softmobile envía eventos al conector mediante webhooks.",
    )
    supports_pull: bool = Field(
        default=True,
        description="Indica si el conector consulta datos directamente de la API.",
    )
    events: list[str] = Field(
        default_factory=list,
        description="Eventos estándar publicados para la integración.",
    )
    documentation_url: str | None = Field(
        default=None,
        description="Enlace de referencia con la documentación técnica del conector.",
    )
    credential: IntegrationCredentialInfo
    health: IntegrationHealthStatus

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "slug": "zapier",
                "name": "Zapier Inventory Bridge",
                "category": "automatizacion",
                "status": "active",
                "supports_push": True,
                "supports_pull": True,
                "events": [
                    "inventory.device.updated",
                    "sales.order.completed",
                ],
                "documentation_url": "https://docs.softmobile.mx/integraciones/zapier",
                "credential": {
                    "token_hint": "XyZ9",
                    "rotated_at": "2025-10-01T06:00:00+00:00",
                    "expires_at": "2025-12-30T06:00:00+00:00",
                },
                "health": {
                    "status": "operational",
                    "checked_at": "2025-11-05T05:00:00+00:00",
                    "message": "Webhook confirmó respuesta 200 en 120 ms",
                },
            }
        }
    )


class IntegrationProviderDetail(IntegrationProviderSummary):
    """Ficha extendida con capacidades y pasos de despliegue."""

    auth_type: str = Field(
        ...,
        min_length=3,
        max_length=40,
        description="Método de autenticación utilizado (api_key, oauth2, etc.).",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Descripción funcional de la integración.",
    )
    features: dict[str, Any] = Field(
        default_factory=dict,
        description="Mapa de capacidades habilitadas para el conector.",
    )
    setup_instructions: list[str] = Field(
        default_factory=list,
        description="Pasos recomendados para habilitar la integración.",
    )


class IntegrationRotateSecretResponse(BaseModel):
    """Respuesta emitida tras rotar el token de una integración."""

    slug: str = Field(
        ...,
        min_length=3,
        max_length=60,
        description="Identificador del conector actualizado.",
    )
    token: str = Field(
        ...,
        min_length=16,
        max_length=200,
        description="Token API recién emitido en formato URL-safe.",
    )
    credential: IntegrationCredentialInfo

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "slug": "erp_sync",
                "token": "4sV2k1lM...",
                "credential": {
                    "token_hint": "LmN7",
                    "rotated_at": "2025-11-06T05:32:00+00:00",
                    "expires_at": "2026-02-04T05:32:00+00:00",
                },
            }
        }
    )


class IntegrationHealthUpdateRequest(BaseModel):
    """Carga útil enviada por los monitores corporativos."""

    status: str = Field(
        ...,
        min_length=2,
        max_length=40,
        description="Estado reportado (operational, degraded, offline, etc.).",
    )
    message: str | None = Field(
        default=None,
        max_length=200,
        description="Descripción breve del resultado del monitoreo.",
    )


__all__ = [
    "AgingMetric",
    "AnalyticsAgingResponse",
    "AnalyticsComparativeResponse",
    "AnalyticsForecastResponse",
    "AnalyticsProfitMarginResponse",
    "AnalyticsRotationResponse",
    "AnalyticsSalesProjectionResponse",
    "AuditAcknowledgedEntity",
    "AuditAcknowledgementCreate",
    "AuditAcknowledgementResponse",
    "AuditUIExportFormat",
    "AuditUIBulkItem",
    "AuditUIBulkRequest",
    "AuditUIBulkResponse",
    "AuditUIRecord",
    "AuditUIListResponse",
    "AuditHighlight",
    "AuditTrailInfo",
    "AuditLogResponse",
    "SystemLogEntry",
    "SystemErrorEntry",
    "GlobalReportFiltersState",
    "GlobalReportTotals",
    "GlobalReportBreakdownItem",
    "GlobalReportAlert",
    "GlobalReportOverview",
    "GlobalReportSeriesPoint",
    "GlobalReportDashboard",
    "SalesSummaryReport",
    "SalesByProductItem",
    "CashCloseReport",
    "CashDenominationInput",
    "CashRegisterEntryCreate",
    "CashRegisterEntryResponse",
    "CashSessionOpenRequest",
    "CashSessionCloseRequest",
    "CashSessionResponse",
    "AuditReminderEntry",
    "AuditReminderSummary",
    "DashboardAuditAlerts",
    "BackupJobResponse",
    "BackupRunRequest",
    "BackupRestoreRequest",
    "BackupRestoreResponse",
    "BinaryFileResponse",
    "HTMLDocumentResponse",
    "IntegrationCredentialInfo",
    "IntegrationHealthStatus",
    "IntegrationProviderSummary",
    "IntegrationProviderDetail",
    "IntegrationRotateSecretResponse",
    "IntegrationHealthUpdateRequest",
    "BackupExportFormat",
    "DeviceBase",
    "DeviceCreate",
    "DeviceResponse",
    "DeviceIdentifierRequest",
    "DeviceIdentifierResponse",
    "DeviceUpdate",
    "SmartImportColumnMatch",
    "InventorySmartImportPreview",
    "InventorySmartImportResult",
    "InventorySmartImportResponse",
    "InventoryImportError",
    "InventoryImportSummary",
    "ImportValidation",
    "ImportValidationDevice",
    "ImportValidationDetail",
    "ImportValidationSummary",
    "InventoryImportHistoryEntry",
    "InventoryMetricsResponse",
    "InventorySummary",
    "InventoryAvailabilityStore",
    "InventoryAvailabilityRecord",
    "InventoryAvailabilityResponse",
    "DashboardChartPoint",
    "DashboardGlobalMetrics",
    "InventoryTotals",
    "LowStockDevice",
    "InventoryAlertDevice",
    "InventoryAlertSummary",
    "InventoryAlertSettingsResponse",
    "InventoryAlertsResponse",
    "MovementBase",
    "MovementCreate",
    "MovementResponse",
    "PurchaseOrderCreate",
    "PurchaseOrderItemCreate",
    "PurchaseOrderItemResponse",
    "PurchaseOrderResponse",
    "PurchaseReceiveItem",
    "PurchaseReceiveRequest",
    "PurchaseImportResponse",
    "PurchaseSuggestionItem",
    "PurchaseSuggestionStore",
    "PurchaseSuggestionsResponse",
    "POSCartItem",
    "POSSalePaymentInput",
    "POSSaleRequest",
    "POSSaleResponse",
    "POSPromotionFeatureFlags",
    "POSVolumePromotion",
    "POSComboPromotionItem",
    "POSComboPromotion",
    "POSCouponPromotion",
    "POSPromotionsConfig",
    "POSPromotionsUpdate",
    "POSPromotionsResponse",
    "POSAppliedPromotion",
    "POSReceiptDeliveryChannel",
    "POSReceiptDeliveryRequest",
    "POSReceiptDeliveryResponse",
    "POSSessionOpenPayload",
    "POSSessionClosePayload",
    "POSSessionSummary",
    "POSTaxInfo",
    "POSReturnItemRequest",
    "PriceListBase",
    "PriceListCreate",
    "PriceListItemBase",
    "PriceListItemCreate",
    "PriceListItemResponse",
    "PriceListItemUpdate",
    "PriceListResponse",
    "PriceListUpdate",
    "PriceResolution",
    "POSReturnRequest",
    "POSReturnResponse",
    "POSSaleDetailResponse",
    "POSElectronicPaymentResult",
    "PurchaseVendorBase",
    "PurchaseVendorCreate",
    "PurchaseVendorUpdate",
    "PurchaseVendorResponse",
    "PurchaseVendorStatusUpdate",
    "PurchaseRecordItemBase",
    "PurchaseRecordItemCreate",
    "PurchaseRecordItemResponse",
    "PurchaseRecordCreate",
    "PurchaseRecordResponse",
    "PurchaseVendorHistory",
    "PurchaseReportFilters",
    "PurchaseReportTotals",
    "PurchaseReportItem",
    "PurchaseReport",
    "PurchaseVendorRanking",
    "PurchaseUserRanking",
    "PurchaseStatistics",
    "PurchaseReturnCreate",
    "PurchaseReturnResponse",
    "RecurringOrderCreate",
    "RecurringOrderExecutionResult",
    "RecurringOrderResponse",
    "OperationHistoryEntry",
    "OperationHistoryTechnician",
    "OperationHistoryType",
    "OperationsHistoryResponse",
    "ReturnRecordType",
    "ReturnRecord",
    "ReturnsTotals",
    "ReturnsOverview",
    "SaleCreate",
    "SaleUpdate",
    "SaleItemCreate",
    "SaleItemResponse",
    "SaleStoreSummary",
    "SaleUserSummary",
    "SaleDeviceSummary",
    "SaleResponse",
    "SaleReturnCreate",
    "SaleReturnItem",
    "SaleReturnResponse",
    "SaleHistorySearchResponse",
    "SalesReportFilters",
    "SalesReportTotals",
    "SalesReportItem",
    "SalesReportGroup",
    "SalesReportProduct",
    "SalesReport",
    "POSConnectorType",
    "POSPrinterMode",
    "POSConnectorSettings",
    "POSPrinterSettings",
    "POSCashDrawerSettings",
    "POSCustomerDisplaySettings",
    "POSHardwareSettings",
    "POSHardwarePrintTestRequest",
    "POSHardwareDrawerOpenRequest",
    "POSHardwareDisplayPushRequest",
    "POSHardwareActionResponse",
    "POSDraftResponse",
    "POSConfigResponse",
    "POSTerminalConfig",
    "POSConfigUpdate",
    "ReleaseInfo",
    "RootWelcomeResponse",
    "RoleResponse",
    "StoreBase",
    "StoreCreate",
    "StoreResponse",
    "StoreUpdate",
    "StoreValueMetric",
    "StoreComparativeMetric",
    "SupplierBase",
    "SupplierBatchBase",
    "SupplierBatchCreate",
    "SupplierBatchOverviewItem",
    "SupplierBatchResponse",
    "SupplierBatchUpdate",
    "SupplierCreate",
    "SupplierResponse",
    "SupplierUpdate",
    "SyncRequest",
    "SyncOutboxEntryResponse",
    "SyncOutboxPriority",
    "SyncOutboxStatsEntry",
    "SyncQueueProgressSummary",
    "SyncHybridComponentSummary",
    "SyncHybridProgressComponents",
    "SyncHybridProgressSummary",
    "SyncHybridForecast",
    "SyncHybridModuleBreakdownComponent",
    "SyncHybridModuleBreakdownItem",
    "SyncHybridRemainingBreakdown",
    "SyncHybridOverview",
    "SyncQueueEvent",
    "SyncQueueEntryResponse",
    "SyncQueueAttemptResponse",
    "SyncQueueEnqueueRequest",
    "SyncQueueEnqueueResponse",
    "SyncQueueDispatchResult",
    "SyncBranchHealth",
    "SyncBranchOverview",
    "SyncBranchStoreDetail",
    "SyncConflictLog",
    "SyncConflictReport",
    "SyncConflictReportFilters",
    "SyncConflictReportTotals",
    "SyncSessionCompact",
    "SyncStoreHistory",
    "SyncOutboxReplayRequest",
    "SyncSessionResponse",
    "TransferReport",
    "TransferReportDevice",
    "TransferReportFilters",
    "TransferReportItem",
    "TransferReportTotals",
    "TokenPayload",
    "TokenVerificationRequest",
    "TokenVerificationResponse",
    "TokenResponse",
    "SessionLoginResponse",
    "PasswordRecoveryRequest",
    "PasswordResetConfirm",
    "PasswordResetResponse",
    "UpdateStatus",
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserRolesUpdate",
    "UserStatusUpdate",
    "RoleModulePermission",
    "RolePermissionMatrix",
    "RolePermissionUpdate",
    "UserDirectoryFilters",
    "UserDirectoryTotals",
    "UserDirectoryEntry",
    "UserDirectoryReport",
    "UserDashboardActivity",
    "UserSessionSummary",
    "UserDashboardMetrics",
    "ProfitMarginMetric",
    "RotationMetric",
    "SalesProjectionMetric",
    "StockoutForecastMetric",
    "HealthStatusResponse",
    "CustomerDebtSnapshot",
    "CreditScheduleEntry",
    "CustomerPaymentReceiptResponse",
    "DashboardReceivableCustomer",
    "DashboardReceivableMetrics",
]

CashSessionCloseRequest.model_rebuild()
CashSessionResponse.model_rebuild()
