"""Modelos ORM del dominio de Softmobile Central."""
from __future__ import annotations

import enum
import json
from datetime import date, datetime, timedelta
import secrets
from uuid import uuid4
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Index,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.sql import column, false
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from ..database import Base


class MovementType(str, enum.Enum):
    """Tipos permitidos de movimientos de inventario."""

    IN = "entrada"
    OUT = "salida"
    ADJUST = "ajuste"


class ReturnDisposition(str, enum.Enum):
    """Clasificación operativa de los artículos devueltos."""

    VENDIBLE = "vendible"
    DEFECTUOSO = "defectuoso"
    NO_VENDIBLE = "no_vendible"
    REPARACION = "reparacion"


RETURN_DISPOSITION_ENUM = Enum(
    ReturnDisposition, name="return_disposition"
)


class ReturnReasonCategory(str, enum.Enum):
    """Categorias corporativas para motivos de devolución."""

    DEFECTO = "defecto"
    LOGISTICA = "logistica"
    CLIENTE = "cliente"
    PRECIO = "precio"
    OTRO = "otro"


RETURN_REASON_CATEGORY_ENUM = Enum(
    ReturnReasonCategory, name="return_reason_category"
)


class RMAStatus(str, enum.Enum):
    """Flujos principales de una solicitud RMA."""

    PENDIENTE = "PENDIENTE"
    AUTORIZADA = "AUTORIZADA"
    EN_PROCESO = "EN_PROCESO"
    CERRADA = "CERRADA"


RMA_STATUS_ENUM = Enum(RMAStatus, name="rma_status")


def generate_customer_tax_id_placeholder() -> str:
    timestamp_component = datetime.utcnow().strftime("%y%m%d")
    random_component = f"{secrets.randbelow(10**8):08d}"
    digits = f"{timestamp_component}{random_component}"
    return f"{digits[:4]}-{digits[4:8]}-{digits[8:]}"
class WarrantyStatus(str, enum.Enum):
    """Estados del ciclo de vida de una garantía asignada."""

    SIN_GARANTIA = "SIN_GARANTIA"
    ACTIVA = "ACTIVA"
    VENCIDA = "VENCIDA"
    RECLAMO = "RECLAMO"
    RESUELTA = "RESUELTA"


class WarrantyClaimType(str, enum.Enum):
    """Tipos de reclamo soportados por las garantías."""

    REPARACION = "REPARACION"
    REEMPLAZO = "REEMPLAZO"


class WarrantyClaimStatus(str, enum.Enum):
    """Estados de procesamiento para los reclamos de garantía."""

    ABIERTO = "ABIERTO"
    EN_PROCESO = "EN_PROCESO"
    RESUELTO = "RESUELTO"
    CANCELADO = "CANCELADO"


WARRANTY_STATUS_ENUM = Enum(WarrantyStatus, name="warranty_status")
WARRANTY_CLAIM_STATUS_ENUM = Enum(WarrantyClaimStatus, name="warranty_claim_status")
WARRANTY_CLAIM_TYPE_ENUM = Enum(WarrantyClaimType, name="warranty_claim_type")


# // [PACK38-inventory-reservations]
class InventoryState(str, enum.Enum):
    """Estados de ciclo de vida de una reserva de inventario."""

    RESERVADO = "RESERVADO"
    CONSUMIDO = "CONSUMIDO"
    CANCELADO = "CANCELADO"
    EXPIRADO = "EXPIRADO"


# // [PACK30-31-BACKEND]
class StockMoveType(str, enum.Enum):
    """Clasificación de movimientos contables por sucursal."""

    IN = "IN"
    OUT = "OUT"
    ADJUST = "ADJ"
    TRANSFER = "TRANSFER"


# // [PACK30-31-BACKEND]
class CostingMethod(str, enum.Enum):
    """Métodos de costeo soportados en la bitácora contable."""

    FIFO = "FIFO"
    AVG = "AVG"


class SyncStatus(str, enum.Enum):
    """Estados posibles de una sesión de sincronización."""

    SUCCESS = "exitoso"
    FAILED = "fallido"


class SyncMode(str, enum.Enum):
    """Modo en el que se dispara la sincronización."""

    AUTOMATIC = "automatico"
    MANUAL = "manual"


class SyncOutboxStatus(str, enum.Enum):
    """Estados posibles de un evento en la cola de sincronización."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class SyncOutboxPriority(str, enum.Enum):
    """Prioridad de procesamiento para eventos híbridos."""

    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class BackupMode(str, enum.Enum):
    """Origen del respaldo generado."""

    AUTOMATIC = "automatico"
    MANUAL = "manual"


class BackupComponent(str, enum.Enum):
    """Componentes disponibles dentro de un respaldo corporativo."""

    DATABASE = "database"
    CONFIGURATION = "configuration"
    CRITICAL_FILES = "critical_files"


class SystemLogLevel(str, enum.Enum):
    """Niveles de severidad admitidos en la bitácora general."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class FeedbackCategory(str, enum.Enum):
    INCIDENTE = "incidente"
    MEJORA = "mejora"
    USABILIDAD = "usabilidad"
    RENDIMIENTO = "rendimiento"
    CONSULTA = "consulta"


class FeedbackPriority(str, enum.Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class FeedbackStatus(str, enum.Enum):
    ABIERTO = "abierto"
    EN_PROGRESO = "en_progreso"
    RESUELTO = "resuelto"
    DESCARTADO = "descartado"


class ConfigRate(Base):
    __tablename__ = "config_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class ConfigXmlTemplate(Base):
    __tablename__ = "config_xml_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    namespace: Mapped[str | None] = mapped_column(String(255), nullable=True)
    schema_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class ConfigParameter(Base):
    __tablename__ = "config_parameters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_type: Mapped[str] = mapped_column(String(20), nullable=False)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Store(Base):
    __tablename__ = "sucursales"

    id: Mapped[int] = mapped_column(
        "id_sucursal", Integer, primary_key=True, index=True
    )
    name: Mapped[str] = mapped_column(
        "nombre", String(120), nullable=False, unique=True, index=True
    )
    location: Mapped[str | None] = mapped_column(
        "direccion", String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(
        "telefono", String(30), nullable=True)
    manager: Mapped[str | None] = mapped_column(
        "responsable", String(120), nullable=True)
    status: Mapped[str] = mapped_column(
        "estado", String(30), nullable=False, default="activa", index=True
    )
    code: Mapped[str] = mapped_column(
        "codigo", String(20), nullable=False, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        "fecha_creacion", DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    timezone: Mapped[str] = mapped_column(
        String(50), nullable=False, default="UTC")
    inventory_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )

    devices: Mapped[list["Device"]] = relationship(
        "Device", back_populates="store", cascade="all, delete-orphan"
    )
    movements: Mapped[list["InventoryMovement"]] = relationship(
        "InventoryMovement",
        back_populates="store",
        cascade="all, delete-orphan",
        foreign_keys="InventoryMovement.store_id",
    )
    sync_sessions: Mapped[list["SyncSession"]] = relationship(
        "SyncSession", back_populates="store", cascade="all, delete-orphan"
    )
    supplier_batches: Mapped[list["SupplierBatch"]] = relationship(
        "SupplierBatch", back_populates="store", cascade="all, delete-orphan"
    )
    users: Mapped[list["User"]] = relationship("User", back_populates="store")
    reservations: Mapped[list["InventoryReservation"]] = relationship(
        "InventoryReservation", back_populates="store", cascade="all, delete-orphan"
    )
    price_lists: Mapped[list["PriceList"]] = relationship(
        "PriceList",
        back_populates="store",
        cascade="all, delete-orphan",
    )
    warehouses: Mapped[list["Warehouse"]] = relationship(
        "Warehouse", back_populates="store", cascade="all, delete-orphan"
    )
    bundles: Mapped[list["ProductBundle"]] = relationship(
        "ProductBundle",
        back_populates="store",
        cascade="all, delete-orphan",
    )


class CommercialState(str, enum.Enum):
    """Clasificación comercial del dispositivo en catálogo pro."""

    NUEVO = "nuevo"
    A = "A"
    B = "B"
    C = "C"


class Warehouse(Base):
    __tablename__ = "warehouses"

    __table_args__ = (
        UniqueConstraint("store_id", "code", name="uq_warehouse_store_code"),
        UniqueConstraint("store_id", "name", name="uq_warehouse_store_name"),
        Index("ix_warehouses_store_id", "store_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sucursales.id_sucursal", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    store: Mapped[Store] = relationship("Store", back_populates="warehouses")
    devices: Mapped[list["Device"]] = relationship("Device", back_populates="warehouse")
    inventory_movements: Mapped[list["InventoryMovement"]] = relationship(
        "InventoryMovement",
        back_populates="warehouse",
        foreign_keys="InventoryMovement.warehouse_id",
        cascade="all, delete-orphan",
    )
    source_inventory_movements: Mapped[list["InventoryMovement"]] = relationship(
        "InventoryMovement",
        back_populates="source_warehouse",
        foreign_keys="InventoryMovement.source_warehouse_id",
        cascade="all, delete-orphan",
    )


class TransferStatus(str, enum.Enum):
    """Estados posibles de una orden de transferencia."""

    SOLICITADA = "SOLICITADA"
    EN_TRANSITO = "EN_TRANSITO"
    RECIBIDA = "RECIBIDA"
    RECHAZADA = "RECHAZADA"
    CANCELADA = "CANCELADA"


class PurchaseStatus(str, enum.Enum):
    """Estados de avance para las órdenes de compra."""

    BORRADOR = "BORRADOR"
    PENDIENTE = "PENDIENTE"
    APROBADA = "APROBADA"
    ENVIADA = "ENVIADA"
    PARCIAL = "PARCIAL"
    COMPLETADA = "COMPLETADA"
    CANCELADA = "CANCELADA"


class RepairStatus(str, enum.Enum):
    """Estados de una orden de reparación."""

    PENDIENTE = "PENDIENTE"
    EN_PROCESO = "EN_PROCESO"
    LISTO = "LISTO"
    ENTREGADO = "ENTREGADO"
    CANCELADO = "CANCELADO"  # // [PACK37-backend]

    @classmethod  # // [PACK37-backend]
    def _missing_(cls, value: object) -> "RepairStatus | None":
        if not isinstance(value, str):
            return None
        normalized = value.strip().upper()
        aliases: dict[str, "RepairStatus"] = {
            "NEW": cls.PENDIENTE,
            "IN_PROGRESS": cls.EN_PROCESO,
            "READY": cls.LISTO,
            "DELIVERED": cls.ENTREGADO,
            "CANCELLED": cls.CANCELADO,
        }
        return aliases.get(normalized)


class RepairPartSource(str, enum.Enum):  # // [PACK37-backend]
    """Origen del repuesto utilizado en la orden."""

    STOCK = "STOCK"
    EXTERNAL = "EXTERNAL"


class CashSessionStatus(str, enum.Enum):
    """Ciclo de vida de un arqueo de caja POS."""

    ABIERTO = "ABIERTO"
    CERRADO = "CERRADO"


class CashEntryType(str, enum.Enum):
    """Tipos de movimientos manuales registrados en caja."""

    INGRESO = "INGRESO"
    EGRESO = "EGRESO"


class PaymentMethod(str, enum.Enum):
    """Formas de pago soportadas en las ventas."""

    EFECTIVO = "EFECTIVO"
    TARJETA = "TARJETA"
    CREDITO = "CREDITO"
    TRANSFERENCIA = "TRANSFERENCIA"
    NOTA_CREDITO = "NOTA_CREDITO"
    PUNTOS = "PUNTOS"
    OTRO = "OTRO"


class LoyaltyTransactionType(str, enum.Enum):
    """Clasificación corporativa de movimientos de lealtad."""

    EARN = "earn"
    REDEEM = "redeem"
    ADJUST = "adjust"
    EXPIRATION = "expiration"


LOYALTY_TRANSACTION_TYPE_ENUM = Enum(
    LoyaltyTransactionType, name="loyalty_transaction_type"
)


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("sucursal_id", "warehouse_id", "sku", name="uq_devices_store_warehouse_sku"),
        UniqueConstraint("imei", name="uq_devices_imei"),
        UniqueConstraint("serial", name="uq_devices_serial"),
        Index("ix_devices_warehouse_id", "warehouse_id"),
        Index("ix_devices_sku_lower", func.lower(column("sku"))),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
    )
    sku: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0"))
    minimum_stock: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    reorder_point: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    imei: Mapped[str | None] = mapped_column(
        String(18), nullable=True, unique=True, index=True)
    serial: Mapped[str | None] = mapped_column(
        String(120), nullable=True, unique=True, index=True)
    marca: Mapped[str | None] = mapped_column(String(80), nullable=True)
    modelo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    categoria: Mapped[str | None] = mapped_column(String(80), nullable=True)
    condicion: Mapped[str | None] = mapped_column(String(60), nullable=True)
    color: Mapped[str | None] = mapped_column(String(60), nullable=True)
    capacidad_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capacidad: Mapped[str | None] = mapped_column(String(80), nullable=True)
    estado_comercial: Mapped[CommercialState] = mapped_column(
        Enum(CommercialState, name="estado_comercial"), nullable=False, default=CommercialState.NUEVO
    )
    estado: Mapped[str] = mapped_column(
        String(40), nullable=False, default="disponible")
    proveedor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    costo_unitario: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0"))
    margen_porcentaje: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0"))
    garantia_meses: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    lote: Mapped[str | None] = mapped_column(String(80), nullable=True)
    fecha_compra: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_ingreso: Mapped[date | None] = mapped_column(Date, nullable=True)
    ubicacion: Mapped[str | None] = mapped_column(String(120), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    imagen_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    completo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)

    store: Mapped[Store] = relationship("Store", back_populates="devices")
    warehouse: Mapped[Warehouse | None] = relationship("Warehouse", back_populates="devices")
    movements: Mapped[list["InventoryMovement"]] = relationship(
        "InventoryMovement",
        back_populates="device",
        cascade="all, delete-orphan",
    )
    identifier: Mapped["DeviceIdentifier | None"] = relationship(
        "DeviceIdentifier",
        back_populates="device",
        cascade="all, delete-orphan",
        uselist=False,
    )
    validations: Mapped[list["ImportValidation"]] = relationship(
        "ImportValidation",
        back_populates="device",
        cascade="all, delete-orphan",
    )
    reservations: Mapped[list["InventoryReservation"]] = relationship(
        "InventoryReservation",
        back_populates="device",
        cascade="all, delete-orphan",
    )
    price_list_items: Mapped[list["PriceListItem"]] = relationship(
        "PriceListItem",
        back_populates="device",
        cascade="all, delete-orphan",
    )
    variants: Mapped[list["ProductVariant"]] = relationship(
        "ProductVariant",
        back_populates="device",
        cascade="all, delete-orphan",
        order_by="ProductVariant.variant_sku",
    )
    bundle_items: Mapped[list["ProductBundleItem"]] = relationship(
        "ProductBundleItem",
        back_populates="device",
        cascade="all, delete-orphan",
    )
    warranty_assignments: Mapped[list["WarrantyAssignment"]] = relationship(
        "WarrantyAssignment",
        back_populates="device",
        cascade="all, delete-orphan",
    )

    @property
    def has_variants(self) -> bool:
        return bool(self.variants)

    @property
    def variant_count(self) -> int:
        return len(self.variants)

    @property
    def costo_compra(self) -> Decimal:
        """Alias semántico de ``costo_unitario`` para reportes corporativos."""

        return self.costo_unitario

    @costo_compra.setter
    def costo_compra(self, value: Decimal) -> None:
        self.costo_unitario = value

    @property
    def precio_venta(self) -> Decimal:
        """Alias semántico de ``unit_price`` para el catálogo de productos."""

        return self.unit_price

    @precio_venta.setter
    def precio_venta(self, value: Decimal) -> None:
        self.unit_price = value


class ProductVariant(Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint(
            "device_id", "variant_sku", name="uq_product_variants_device_sku"
        ),
        Index("ix_product_variants_device_id", "device_id"),
        Index("ix_product_variants_variant_sku", "variant_sku"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    variant_sku: Mapped[str] = mapped_column(String(80), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(120), nullable=True)
    unit_price_override: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    device: Mapped["Device"] = relationship("Device", back_populates="variants")
    bundle_items: Mapped[list["ProductBundleItem"]] = relationship(
        "ProductBundleItem",
        back_populates="variant",
        cascade="all, delete-orphan",
    )

    @property
    def store_id(self) -> int:
        return self.device.store_id

    @property
    def device_sku(self) -> str:
        return self.device.sku

    @property
    def device_name(self) -> str:
        return self.device.name


class ProductBundle(Base):
    __tablename__ = "product_bundles"
    __table_args__ = (
        UniqueConstraint(
            "store_id", "bundle_sku", name="uq_product_bundles_store_sku"
        ),
        Index("ix_product_bundles_store_id", "store_id"),
        Index("ix_product_bundles_bundle_sku", "bundle_sku"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    bundle_sku: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    store: Mapped[Optional[Store]] = relationship("Store", back_populates="bundles")
    items: Mapped[list["ProductBundleItem"]] = relationship(
        "ProductBundleItem",
        back_populates="bundle",
        cascade="all, delete-orphan",
    )


class ProductBundleItem(Base):
    __tablename__ = "product_bundle_items"
    __table_args__ = (
        Index("ix_product_bundle_items_bundle_id", "bundle_id"),
        Index("ix_product_bundle_items_device_id", "device_id"),
        Index("ix_product_bundle_items_variant_id", "variant_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    bundle_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("product_bundles.id", ondelete="CASCADE"),
        nullable=False,
    )
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    variant_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    bundle: Mapped["ProductBundle"] = relationship(
        "ProductBundle", back_populates="items"
    )
    device: Mapped["Device"] = relationship("Device", back_populates="bundle_items")
    variant: Mapped[Optional["ProductVariant"]] = relationship(
        "ProductVariant", back_populates="bundle_items"
    )

    @property
    def device_sku(self) -> str:
        return self.device.sku

    @property
    def device_name(self) -> str:
        return self.device.name





class DeviceIdentifier(Base):
    __tablename__ = "device_identifiers"
    __table_args__ = (
        UniqueConstraint("producto_id", name="uq_device_identifiers_producto"),
        UniqueConstraint("imei_1", name="uq_device_identifiers_imei_1"),
        UniqueConstraint("imei_2", name="uq_device_identifiers_imei_2"),
        UniqueConstraint(
            "numero_serie", name="uq_device_identifiers_numero_serie"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    producto_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    imei_1: Mapped[str | None] = mapped_column(String(18), nullable=True)
    imei_2: Mapped[str | None] = mapped_column(String(18), nullable=True)
    numero_serie: Mapped[str | None] = mapped_column(
        String(120), nullable=True)
    estado_tecnico: Mapped[str | None] = mapped_column(
        String(60), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    device: Mapped[Device] = relationship(
        "Device", back_populates="identifier")


class WMSBin(Base):
    """Ubicación física (bin) dentro de una sucursal para WMS ligero."""

    __tablename__ = "wms_bins"
    __table_args__ = (
        UniqueConstraint("sucursal_id", "codigo",
                         name="uq_wms_bins_store_code"),
        Index("ix_wms_bins_store", "sucursal_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column("codigo", String(60), nullable=False)
    aisle: Mapped[str | None] = mapped_column(
        "pasillo", String(60), nullable=True)
    rack: Mapped[str | None] = mapped_column(String(60), nullable=True)
    level: Mapped[str | None] = mapped_column(
        "nivel", String(60), nullable=True)
    description: Mapped[str | None] = mapped_column(
        "descripcion", String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column("fecha_creacion", DateTime(
        timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column("fecha_actualizacion", DateTime(
        timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    store: Mapped[Store] = relationship("Store")
    assignments: Mapped[list["DeviceBinAssignment"]] = relationship(
        "DeviceBinAssignment", back_populates="bin", cascade="all, delete-orphan"
    )


class DeviceBinAssignment(Base):
    """Asociación actual/histórica entre un dispositivo y un bin."""

    __tablename__ = "device_bins"
    __table_args__ = (
        Index("ix_device_bins_device", "producto_id"),
        Index("ix_device_bins_bin", "bin_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(
        "producto_id", Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    bin_id: Mapped[int] = mapped_column(Integer, ForeignKey(
        "wms_bins.id", ondelete="CASCADE"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column("asignado_en", DateTime(
        timezone=True), default=datetime.utcnow, nullable=False)
    unassigned_at: Mapped[datetime | None] = mapped_column(
        "desasignado_en", DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(
        "activo", Boolean, default=True, nullable=False)

    device: Mapped[Device] = relationship("Device")
    bin: Mapped[WMSBin] = relationship("WMSBin", back_populates="assignments")


class PriceList(Base):
    """Catálogo de precios segmentado por sucursal o cliente."""

    __tablename__ = "price_lists"
    __table_args__ = (
        UniqueConstraint(
            "name", "store_id", "customer_id", name="uq_price_lists_scope_name"
        ),
        Index("ix_price_lists_name", "name"),
        Index("ix_price_lists_is_active", "is_active"),
        Index("ix_price_lists_priority", "priority"),
        Index("ix_price_lists_store_id", "store_id"),
        Index("ix_price_lists_customer_id", "customer_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    store_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="SET NULL"),
        nullable=True,
    )
    customer_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("clientes.id_cliente", ondelete="SET NULL"),
        nullable=True,
    )
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="MXN")
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    store: Mapped[Store | None] = relationship("Store", back_populates="price_lists")
    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer", back_populates="price_lists"
    )
    items: Mapped[list["PriceListItem"]] = relationship(
        "PriceListItem", back_populates="price_list", cascade="all, delete-orphan"
    )

    @property
    def scope(self) -> str:
        if self.store_id is not None and self.customer_id is not None:
            return "store_customer"
        if self.customer_id is not None:
            return "customer"
        if self.store_id is not None:
            return "store"
        return "global"


class PriceListItem(Base):
    """Precio específico de un dispositivo dentro de una lista."""

    __tablename__ = "price_list_items"
    __table_args__ = (
        UniqueConstraint(
            "price_list_id", "device_id", name="uq_price_list_items_price_device"
        ),
        Index("ix_price_list_items_list_device", "price_list_id", "device_id"),
        Index("ix_price_list_items_price_list", "price_list_id"),
        Index("ix_price_list_items_device", "device_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    price_list_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("price_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="MXN")
    discount_percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    price_list: Mapped[PriceList] = relationship(
        "PriceList", back_populates="items"
    )
    device: Mapped[Device] = relationship(
        "Device", back_populates="price_list_items"
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    users: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan"
    )
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", back_populates="role", cascade="all, delete-orphan"
    )


class Permission(Base):
    __tablename__ = "permisos"
    __table_args__ = (
        UniqueConstraint("rol", "modulo", name="uq_permisos_rol_modulo"),
    )

    id: Mapped[int] = mapped_column(
        "id_permiso", Integer, primary_key=True, index=True)
    role_name: Mapped[str] = mapped_column(
        "rol",
        String(50),
        ForeignKey("roles.name", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    module: Mapped[str] = mapped_column(
        "modulo", String(120), nullable=False, index=True)
    can_view: Mapped[bool] = mapped_column(
        "puede_ver", Boolean, nullable=False, default=False)
    can_edit: Mapped[bool] = mapped_column(
        "puede_editar", Boolean, nullable=False, default=False)
    can_delete: Mapped[bool] = mapped_column(
        "puede_borrar", Boolean, nullable=False, default=False)

    rol = synonym("role_name")

    role: Mapped[Role] = relationship("Role", back_populates="permissions")


class User(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(
        "id_usuario", Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column("correo", String(
        120), nullable=False, unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(
        "nombre", String(120), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)
    rol: Mapped[str] = mapped_column(
        String(30), nullable=False, default="OPERADOR", server_default="OPERADOR")
    estado: Mapped[str] = mapped_column(
        String(30), nullable=False, default="ACTIVO", server_default="ACTIVO")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    supervisor_pin_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        "fecha_creacion", DateTime(timezone=True), default=datetime.utcnow
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    last_login_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    store_id: Mapped[int | None] = mapped_column(
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    correo = synonym("username")
    nombre = synonym("full_name")

    roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="user", cascade="all, delete-orphan"
    )
    movements: Mapped[list["InventoryMovement"]] = relationship(
        "InventoryMovement", back_populates="performed_by")
    sync_sessions: Mapped[list["SyncSession"]] = relationship(
        "SyncSession", back_populates="triggered_by")
    logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="performed_by")
    backup_jobs: Mapped[list["BackupJob"]] = relationship(
        "BackupJob", back_populates="triggered_by")
    totp_secret: Mapped[UserTOTPSecret | None] = relationship(
        "UserTOTPSecret", back_populates="user", uselist=False
    )
    store: Mapped[Store | None] = relationship("Store", back_populates="users")
    active_sessions: Mapped[list["ActiveSession"]] = relationship(
        "ActiveSession",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="ActiveSession.user_id",
    )
    audit_acknowledgements: Mapped[list["AuditAlertAcknowledgement"]] = relationship(
        "AuditAlertAcknowledgement",
        back_populates="acknowledged_by",
        cascade="all, delete-orphan",
    )
    inventory_reservations: Mapped[list["InventoryReservation"]] = relationship(
        "InventoryReservation",
        back_populates="reserved_by",
        cascade="all, delete-orphan",
        foreign_keys="InventoryReservation.reserved_by_id",
    )
    resolved_reservations: Mapped[list["InventoryReservation"]] = relationship(
        "InventoryReservation",
        back_populates="resolved_by",
        cascade="all, delete-orphan",
        foreign_keys="InventoryReservation.resolved_by_id",
    )
    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint(
        "user_id", "role_id", name="uq_user_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(
        "usuarios.id_usuario", ondelete="CASCADE"), index=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey(
        "roles.id", ondelete="CASCADE"), index=True)

    user: Mapped[User] = relationship("User", back_populates="roles")
    role: Mapped[Role] = relationship("Role", back_populates="users")


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        Index(
            "ix_inventory_movements_store_fecha",
            "sucursal_destino_id",
            "fecha",
        ),
        Index("ix_inventory_movements_fecha", "fecha"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        "sucursal_destino_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="CASCADE"),
        index=True,
    )
    source_store_id: Mapped[int | None] = mapped_column(
        "sucursal_origen_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    warehouse_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_warehouse_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    device_id: Mapped[int] = mapped_column(
        "producto_id",
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        index=True,
    )
    movement_type: Mapped[MovementType] = mapped_column(
        "tipo_movimiento", Enum(MovementType, name="movement_type"), nullable=False
    )
    quantity: Mapped[int] = mapped_column("cantidad", Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(
        "comentario", String(255), nullable=True)
    unit_cost: Mapped[Decimal | None] = mapped_column(
        "costo_unitario", Numeric(12, 2), nullable=True
    )
    performed_by_id: Mapped[int | None] = mapped_column(
        "usuario_id",
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        "fecha", DateTime(timezone=True), default=datetime.utcnow
    )

    store: Mapped[Store] = relationship(
        "Store",
        back_populates="movements",
        foreign_keys=[store_id],
    )
    source_store: Mapped[Store | None] = relationship(
        "Store",
        foreign_keys=[source_store_id],
    )
    warehouse: Mapped[Warehouse | None] = relationship(
        "Warehouse", foreign_keys=[warehouse_id], back_populates="inventory_movements"
    )
    source_warehouse: Mapped[Warehouse | None] = relationship(
        "Warehouse", foreign_keys=[source_warehouse_id], back_populates="source_inventory_movements"
    )
    device: Mapped[Device] = relationship("Device", back_populates="movements")
    performed_by: Mapped[User | None] = relationship(
        "User", back_populates="movements")

    @property
    def usuario(self) -> str | None:
        """Nombre descriptivo del usuario que registró el movimiento."""

        if self.performed_by is None:
            return None
        if self.performed_by.full_name:
            return self.performed_by.full_name
        return self.performed_by.username

    @property
    def tienda_origen(self) -> str | None:
        """Nombre de la sucursal de origen, si aplica."""

        if self.source_store is None:
            return None
        return self.source_store.name

    @property
    def tienda_destino(self) -> str | None:
        """Nombre de la sucursal destino."""

        if self.store is None:
            return None
        return self.store.name

    @property
    def sucursal_origen(self) -> str | None:
        return self.tienda_origen

    @property
    def sucursal_destino(self) -> str | None:
        return self.tienda_destino


class InventoryReservation(Base):
    """Bloqueo temporal de existencias para ventas o transferencias."""

    __tablename__ = "inventory_reservations"
    __table_args__ = (
        Index("ix_inventory_reservation_store_device", "store_id", "device_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="CASCADE"),
        nullable=False,
    )
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    reserved_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
    )
    initial_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[InventoryState] = mapped_column(
        Enum(InventoryState, name="inventory_reservation_state"),
        nullable=False,
        default=InventoryState.RESERVADO,
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    resolution_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    store: Mapped[Store] = relationship("Store", back_populates="reservations")
    device: Mapped[Device] = relationship("Device", back_populates="reservations")
    reserved_by: Mapped[User | None] = relationship(
        "User", back_populates="inventory_reservations", foreign_keys=[reserved_by_id]
    )
    resolved_by: Mapped[User | None] = relationship(
        "User", back_populates="resolved_reservations", foreign_keys=[resolved_by_id]
    )
    sale_items: Mapped[list["SaleItem"]] = relationship(
        "SaleItem", back_populates="reservation"
    )
    transfer_items: Mapped[list["TransferOrderItem"]] = relationship(
        "TransferOrderItem", back_populates="reservation"
    )


# // [PACK30-31-BACKEND]
class StockMove(Base):
    __tablename__ = "stock_moves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    branch_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    movement_type: Mapped[StockMoveType] = mapped_column(
        Enum(StockMoveType, name="stock_move_type"), nullable=False
    )
    reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True
    )

    product: Mapped["Device"] = relationship("Device")
    branch: Mapped[Store | None] = relationship("Store")
    ledger_entries: Mapped[list["CostLedgerEntry"]] = relationship(
        "CostLedgerEntry", back_populates="move", cascade="all, delete-orphan"
    )


# // [PACK30-31-BACKEND]
class CostLedgerEntry(Base):
    __tablename__ = "cost_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    move_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stock_moves.id", ondelete="CASCADE"), nullable=False, index=True
    )
    branch_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    method: Mapped[CostingMethod] = mapped_column(
        Enum(CostingMethod, name="costing_method"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True
    )

    move: Mapped[StockMove] = relationship(
        "StockMove", back_populates="ledger_entries")
    product: Mapped["Device"] = relationship("Device")
    branch: Mapped[Store | None] = relationship("Store")


class SyncSession(Base):
    __tablename__ = "sync_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int | None] = mapped_column(
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    mode: Mapped[SyncMode] = mapped_column(
        Enum(SyncMode, name="sync_mode"), nullable=False)
    status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus, name="sync_status"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )

    store: Mapped[Store | None] = relationship(
        "Store", back_populates="sync_sessions")
    triggered_by: Mapped[User | None] = relationship(
        "User", back_populates="sync_sessions")


class AuditUI(Base):
    """Eventos de interacción registrados desde la interfaz de usuario."""

    __tablename__ = "audit_ui"

    # // [PACK32-33-BE] Retención sugerida: conservar 180 días y depurar con job programado.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(
        String(120), nullable=True, index=True)
    module: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    action: Mapped[str] = mapped_column(
        String(120), nullable=False, index=True)
    entity_id: Mapped[str | None] = mapped_column(
        String(120), nullable=True, index=True)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class SupportFeedback(Base):
    """Sugerencias, incidencias y mejoras reportadas por usuarios corporativos."""

    __tablename__ = "support_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tracking_id: Mapped[str] = mapped_column(
        String(36), default=lambda: str(uuid4()), unique=True, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    contact: Mapped[str | None] = mapped_column(String(180), nullable=True)
    module: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    category: Mapped[FeedbackCategory] = mapped_column(
        Enum(FeedbackCategory, name="feedback_category"), nullable=False
    )
    priority: Mapped[FeedbackPriority] = mapped_column(
        Enum(FeedbackPriority, name="feedback_priority"), nullable=False, default=FeedbackPriority.MEDIA
    )
    status: Mapped[FeedbackStatus] = mapped_column(
        Enum(FeedbackStatus, name="feedback_status"), nullable=False, default=FeedbackStatus.ABIERTO
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    usage_context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(80), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)

    performed_by: Mapped[User | None] = relationship(
        "User", back_populates="logs")
    system_log: Mapped[Optional["SystemLog"]] = relationship(
        "SystemLog", back_populates="audit_log", uselist=False
    )

    @property
    def module(self) -> str | None:
        """Nombre del módulo asociado al evento de auditoría."""

        if self.system_log is None:
            return None
        return self.system_log.modulo


class AuditAlertAcknowledgement(Base):
    __tablename__ = "audit_alert_acknowledgements"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id",
                         name="uq_audit_ack_entity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(
        String(80), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(
        String(80), nullable=False, index=True)
    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    acknowledged_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    acknowledged_by: Mapped[User | None] = relationship(
        "User", back_populates="audit_acknowledgements"
    )


class SystemLog(Base):
    __tablename__ = "logs_sistema"

    id: Mapped[int] = mapped_column(
        "id_log", Integer, primary_key=True, index=True)
    usuario: Mapped[str | None] = mapped_column(
        String(120), nullable=True, index=True)
    modulo: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    accion: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
    nivel: Mapped[SystemLogLevel] = mapped_column(
        Enum(SystemLogLevel, name="system_log_level"), nullable=False, index=True
    )
    ip_origen: Mapped[str | None] = mapped_column(String(45), nullable=True)
    audit_log_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("audit_logs.id", ondelete="SET NULL"), nullable=True, unique=True
    )

    audit_log: Mapped[AuditLog | None] = relationship(
        "AuditLog", back_populates="system_log")


class SystemError(Base):
    __tablename__ = "errores_sistema"

    id: Mapped[int] = mapped_column(
        "id_error", Integer, primary_key=True, index=True)
    mensaje: Mapped[str] = mapped_column(String(255), nullable=False)
    stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)
    modulo: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
    usuario: Mapped[str | None] = mapped_column(
        String(120), nullable=True, index=True)


class InventoryImportTemp(Base):
    __tablename__ = "importaciones_temp"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre_archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    columnas_detectadas: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    registros_incompletos: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    total_registros: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    nuevos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actualizados: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    advertencias: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list)
    patrones_columnas: Mapped[dict[str, str]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    duracion_segundos: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )


class ImportValidation(Base):
    __tablename__ = "validaciones_importacion"

    id: Mapped[int] = mapped_column(
        "id_validacion", Integer, primary_key=True, index=True
    )
    producto_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    tipo: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    severidad: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
    corregido: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)

    device: Mapped["Device | None"] = relationship(
        "Device", back_populates="validations"
    )


class BackupJob(Base):
    __tablename__ = "backup_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mode: Mapped[BackupMode] = mapped_column(
        Enum(BackupMode, name="backup_mode"), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    pdf_path: Mapped[str] = mapped_column(String(255), nullable=False)
    archive_path: Mapped[str] = mapped_column(String(255), nullable=False)
    json_path: Mapped[str] = mapped_column(String(255), nullable=False)
    sql_path: Mapped[str] = mapped_column(String(255), nullable=False)
    config_path: Mapped[str] = mapped_column(String(255), nullable=False)
    metadata_path: Mapped[str] = mapped_column(String(255), nullable=False)
    critical_directory: Mapped[str] = mapped_column(
        String(255), nullable=False)
    components: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list)
    total_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    triggered_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )

    triggered_by: Mapped[User | None] = relationship(
        "User", back_populates="backup_jobs")


class TransferOrder(Base):
    __tablename__ = "transfer_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    origin_store_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    destination_store_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[TransferStatus] = mapped_column(
        Enum(TransferStatus, name="transfer_status"),
        nullable=False,
        default=TransferStatus.SOLICITADA,
    )
    requested_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    dispatched_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    received_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    cancelled_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    origin_store: Mapped[Store] = relationship(
        "Store", foreign_keys=[origin_store_id], backref="transfer_orders_out"
    )
    destination_store: Mapped[Store] = relationship(
        "Store", foreign_keys=[destination_store_id], backref="transfer_orders_in"
    )
    requested_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[requested_by_id])
    dispatched_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[dispatched_by_id])
    received_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[received_by_id])
    cancelled_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[cancelled_by_id])
    items: Mapped[list["TransferOrderItem"]] = relationship(
        "TransferOrderItem", back_populates="transfer_order", cascade="all, delete-orphan"
    )


class TransferOrderItem(Base):
    __tablename__ = "transfer_order_items"
    __table_args__ = (
        UniqueConstraint("transfer_order_id", "device_id",
                         name="uq_transfer_item_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    transfer_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("transfer_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    dispatched_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    received_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dispatched_unit_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    reservation_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("inventory_reservations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    transfer_order: Mapped[TransferOrder] = relationship(
        "TransferOrder", back_populates="items"
    )
    device: Mapped[Device] = relationship("Device")
    reservation: Mapped["InventoryReservation | None"] = relationship(
        "InventoryReservation", back_populates="transfer_items"
    )


class RecurringOrderType(str, enum.Enum):
    """Tipos disponibles para plantillas recurrentes."""

    PURCHASE = "purchase"
    TRANSFER = "transfer"


class RecurringOrder(Base):
    __tablename__ = "recurring_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    order_type: Mapped[RecurringOrderType] = mapped_column(
        Enum(RecurringOrderType, name="recurring_order_type"),
        nullable=False,
    )
    store_id: Mapped[int | None] = mapped_column(
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict)
    created_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    last_used_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    store: Mapped[Store | None] = relationship("Store")
    created_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[created_by_id], backref="recurring_orders_created"
    )
    last_used_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[last_used_by_id], backref="recurring_orders_used"
    )


class StoreMembership(Base):
    __tablename__ = "store_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "sucursal_id",
                         name="uq_membership_user_store"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False, index=True
    )
    store_id: Mapped[int] = mapped_column(
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    can_create_transfer: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    can_receive_transfer: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)

    user: Mapped[User] = relationship("User", backref="store_memberships")
    store: Mapped[Store] = relationship("Store", backref="memberships")


class Customer(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(
        "id_cliente", Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        "nombre", String(120), nullable=False, unique=True, index=True
    )
    contact_name: Mapped[str | None] = mapped_column(
        String(120), nullable=True)
    email: Mapped[str | None] = mapped_column(
        "correo", String(120), nullable=True, unique=True, index=True
    )
    phone: Mapped[str] = mapped_column(
        "telefono", String(40), nullable=False, index=True
    )
    address: Mapped[str | None] = mapped_column(
        "direccion", String(255), nullable=True)
    customer_type: Mapped[str] = mapped_column(
        "tipo", String(30), nullable=False, default="minorista", index=True
    )
    status: Mapped[str] = mapped_column(
        "estado", String(20), nullable=False, default="activo", index=True
    )
    credit_limit: Mapped[Decimal] = mapped_column(
        "limite_credito", Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    outstanding_debt: Mapped[Decimal] = mapped_column(
        "saldo", Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    notes: Mapped[str | None] = mapped_column("notas", Text, nullable=True)
    history: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list)
    privacy_consents: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict)
    privacy_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict)
    segment_category: Mapped[str | None] = mapped_column(
        "segmento_categoria", String(60), nullable=True, index=True
    )
    tags: Mapped[list[str]] = mapped_column(
        "segmento_etiquetas", JSON, nullable=False, default=list
    )
    tax_id: Mapped[str] = mapped_column(
        "rtn",
        String(30),
        nullable=False,
        unique=True,
        index=True,
        default=generate_customer_tax_id_placeholder,
    )
    privacy_last_request_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    last_interaction_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    repair_orders: Mapped[list["RepairOrder"]] = relationship(
        "RepairOrder", back_populates="customer"
    )
    sales: Mapped[list["Sale"]] = relationship(
        "Sale", back_populates="customer")
    ledger_entries: Mapped[list["CustomerLedgerEntry"]] = relationship(
        "CustomerLedgerEntry",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    store_credits: Mapped[list["StoreCredit"]] = relationship(
        "StoreCredit",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    privacy_requests: Mapped[list["CustomerPrivacyRequest"]] = relationship(
        "CustomerPrivacyRequest",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    price_lists: Mapped[list["PriceList"]] = relationship(
        "PriceList",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    loyalty_account: Mapped[Optional["LoyaltyAccount"]] = relationship(
        "LoyaltyAccount",
        back_populates="customer",
        cascade="all, delete-orphan",
        uselist=False,
    )
    segment_snapshot: Mapped[Optional["CustomerSegmentSnapshot"]] = relationship(
        "CustomerSegmentSnapshot",
        back_populates="customer",
        cascade="all, delete-orphan",
        uselist=False,
    )

    @property
    def annual_purchase_amount(self) -> Decimal:
        snapshot = getattr(self, "segment_snapshot", None)
        if snapshot and snapshot.annual_amount is not None:
            return Decimal(snapshot.annual_amount)
        return Decimal("0")

    @property
    def orders_last_year(self) -> int:
        snapshot = getattr(self, "segment_snapshot", None)
        return int(snapshot.orders_last_year) if snapshot else 0

    @property
    def purchase_frequency(self) -> str:
        snapshot = getattr(self, "segment_snapshot", None)
        return snapshot.frequency_label if snapshot else "sin_datos"

    @property
    def segment_labels(self) -> list[str]:
        snapshot = getattr(self, "segment_snapshot", None)
        if snapshot and snapshot.segment_labels:
            return list(snapshot.segment_labels)
        return []

    @property
    def last_purchase_at(self) -> datetime | None:
        snapshot = getattr(self, "segment_snapshot", None)
        return snapshot.last_sale_at if snapshot else None


class PrivacyRequestType(str, enum.Enum):
    """Tipos de solicitudes de privacidad realizadas por clientes."""

    CONSENT = "consent"
    ANONYMIZATION = "anonymization"


class PrivacyRequestStatus(str, enum.Enum):
    """Estados posibles de una solicitud de privacidad."""

    REGISTRADA = "registrada"
    PROCESADA = "procesada"


class CustomerPrivacyRequest(Base):
    __tablename__ = "customer_privacy_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clientes.id_cliente", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    request_type: Mapped[PrivacyRequestType] = mapped_column(
        Enum(PrivacyRequestType, name="privacy_request_type"), nullable=False
    )
    status: Mapped[PrivacyRequestStatus] = mapped_column(
        Enum(PrivacyRequestStatus, name="privacy_request_status"),
        nullable=False,
        default=PrivacyRequestStatus.PROCESADA,
    )
    details: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consent_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    masked_fields: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processed_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    customer: Mapped[Customer] = relationship(
        "Customer", back_populates="privacy_requests"
    )
    processed_by: Mapped[Optional["User"]] = relationship("User")


class CustomerLedgerEntryType(str, enum.Enum):
    """Tipos de movimientos registrados en la bitácora de clientes."""

    SALE = "sale"
    PAYMENT = "payment"
    ADJUSTMENT = "adjustment"
    NOTE = "note"
    STORE_CREDIT_ISSUED = "store_credit_issued"
    STORE_CREDIT_REDEEMED = "store_credit_redeemed"


class CustomerLedgerEntry(Base):
    __tablename__ = "customer_ledger_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clientes.id_cliente", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_type: Mapped[CustomerLedgerEntryType] = mapped_column(
        Enum(CustomerLedgerEntryType, name="customer_ledger_entry_type"),
        nullable=False,
    )
    reference_type: Mapped[str | None] = mapped_column(
        String(40), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    created_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    customer: Mapped["Customer"] = relationship(
        "Customer", back_populates="ledger_entries"
    )
    created_by: Mapped[Optional["User"]] = relationship("User")


class LoyaltyAccount(Base):
    __tablename__ = "loyalty_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clientes.id_cliente", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    accrual_rate: Mapped[Decimal] = mapped_column(
        Numeric(6, 4), nullable=False, default=Decimal("1.0000")
    )
    redemption_rate: Mapped[Decimal] = mapped_column(
        Numeric(6, 4), nullable=False, default=Decimal("1.0000")
    )
    expiration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=365)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    rule_config: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    balance_points: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    lifetime_points_earned: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    lifetime_points_redeemed: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    expired_points_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    last_accrual_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_redemption_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_expiration_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    customer: Mapped["Customer"] = relationship(
        "Customer", back_populates="loyalty_account"
    )
    transactions: Mapped[list["LoyaltyTransaction"]] = relationship(
        "LoyaltyTransaction",
        back_populates="account",
        cascade="all, delete-orphan",
    )


class LoyaltyTransaction(Base):
    __tablename__ = "loyalty_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("loyalty_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sale_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("ventas.id_venta", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    transaction_type: Mapped[LoyaltyTransactionType] = mapped_column(
        LOYALTY_TRANSACTION_TYPE_ENUM.copy(), nullable=False
    )
    points: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    currency_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    registered_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    account: Mapped["LoyaltyAccount"] = relationship(
        "LoyaltyAccount", back_populates="transactions"
    )
    sale: Mapped["Sale | None"] = relationship(
        "Sale", back_populates="loyalty_transactions"
    )
    registered_by: Mapped[Optional["User"]] = relationship("User")


class StoreCreditStatus(str, enum.Enum):
    """Estados operativos de las notas de crédito emitidas."""

    ACTIVO = "ACTIVO"
    PARCIAL = "PARCIAL"
    REDIMIDO = "REDIMIDO"
    CANCELADO = "CANCELADO"


class StoreCredit(Base):
    __tablename__ = "store_credits"
    __table_args__ = (
        UniqueConstraint("code", name="uq_store_credit_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clientes.id_cliente", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    issued_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    balance_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    status: Mapped[StoreCreditStatus] = mapped_column(
        Enum(StoreCreditStatus, name="store_credit_status"),
        nullable=False,
        default=StoreCreditStatus.ACTIVO,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    redeemed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    issued_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    customer: Mapped["Customer"] = relationship(
        "Customer", back_populates="store_credits"
    )
    issued_by: Mapped[Optional["User"]] = relationship("User")
    redemptions: Mapped[list["StoreCreditRedemption"]] = relationship(
        "StoreCreditRedemption",
        back_populates="store_credit",
        cascade="all, delete-orphan",
    )


class CustomerSegmentSnapshot(Base):
    __tablename__ = "customer_segment_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clientes.id_cliente", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    annual_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    orders_last_year: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_ticket: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    frequency_label: Mapped[str] = mapped_column(
        String(30), nullable=False, default="sin_datos"
    )
    segment_labels: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    last_sale_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    customer: Mapped[Customer] = relationship(
        "Customer", back_populates="segment_snapshot"
    )


class StoreCreditRedemption(Base):
    __tablename__ = "store_credit_redemptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_credit_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("store_credits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sale_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("ventas.id_venta", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    created_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    store_credit: Mapped["StoreCredit"] = relationship(
        "StoreCredit", back_populates="redemptions"
    )
    sale: Mapped[Optional["Sale"]] = relationship(
        "Sale", back_populates="store_credit_redemptions"
    )
    created_by: Mapped[Optional["User"]] = relationship("User")


class SupplierLedgerEntryType(str, enum.Enum):
    """Tipos de movimientos registrados en la bitácora de proveedores."""

    INVOICE = "invoice"
    PAYMENT = "payment"
    CREDIT_NOTE = "credit_note"
    ADJUSTMENT = "adjustment"


class SupplierLedgerEntry(Base):
    __tablename__ = "supplier_ledger_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    supplier_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_type: Mapped[SupplierLedgerEntryType] = mapped_column(
        Enum(SupplierLedgerEntryType, name="supplier_ledger_entry_type"),
        nullable=False,
    )
    reference_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    balance_after: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    created_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    supplier: Mapped["Supplier"] = relationship(
        "Supplier", back_populates="ledger_entries"
    )
    created_by: Mapped[Optional["User"]] = relationship("User")


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(120), nullable=False, unique=True, index=True)
    rtn: Mapped[str | None] = mapped_column(String(30), nullable=True, unique=True)
    payment_terms: Mapped[str | None] = mapped_column(String(80), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(
        String(120), nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    contact_info: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    products_supplied: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list)
    history: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list)
    outstanding_debt: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    batches: Mapped[list["SupplierBatch"]] = relationship(
        "SupplierBatch", back_populates="supplier", cascade="all, delete-orphan"
    )
    ledger_entries: Mapped[list["SupplierLedgerEntry"]] = relationship(
        "SupplierLedgerEntry",
        back_populates="supplier",
        cascade="all, delete-orphan",
    )


class SupplierBatch(Base):
    __tablename__ = "supplier_batches"
    __table_args__ = (
        UniqueConstraint("supplier_id", "batch_code",
                         name="uq_supplier_batch_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    supplier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    store_id: Mapped[int | None] = mapped_column(
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    device_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True
    )
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    batch_code: Mapped[str] = mapped_column(String(80), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    supplier: Mapped["Supplier"] = relationship(
        "Supplier", back_populates="batches")
    store: Mapped[Store | None] = relationship(
        "Store", back_populates="supplier_batches")
    device: Mapped[Device | None] = relationship("Device")


class Proveedor(Base):
    """Catálogo simplificado de proveedores corporativos."""

    __tablename__ = "proveedores"

    id_proveedor: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(
        String(150), nullable=False, unique=True, index=True)
    telefono: Mapped[str | None] = mapped_column(String(40), nullable=True)
    correo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tipo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    estado: Mapped[str] = mapped_column(
        String(40), nullable=False, default="activo")
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    compras: Mapped[list["Compra"]] = relationship(
        "Compra", back_populates="proveedor", cascade="all, delete-orphan"
    )


class Compra(Base):
    """Encabezado de compras directas registradas en el módulo clásico."""

    __tablename__ = "compras"

    id_compra: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True)
    proveedor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("proveedores.id_proveedor", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    usuario_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    impuesto: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    forma_pago: Mapped[str] = mapped_column(String(60), nullable=False)
    estado: Mapped[str] = mapped_column(
        String(40), nullable=False, default="PENDIENTE")

    proveedor: Mapped[Proveedor] = relationship(
        "Proveedor", back_populates="compras")
    usuario: Mapped["User"] = relationship("User")
    detalles: Mapped[list["DetalleCompra"]] = relationship(
        "DetalleCompra", back_populates="compra", cascade="all, delete-orphan"
    )


class DetalleCompra(Base):
    """Detalle de productos asociados a una compra simplificada."""

    __tablename__ = "detalle_compras"

    id_detalle: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True)
    compra_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("compras.id_compra", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    producto_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    costo_unitario: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )

    compra: Mapped[Compra] = relationship("Compra", back_populates="detalles")
    producto: Mapped[Device] = relationship("Device")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    supplier: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[PurchaseStatus] = mapped_column(
        Enum(PurchaseStatus, name="purchase_status"),
        nullable=False,
        default=PurchaseStatus.PENDIENTE,
    )
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    approved_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    requires_approval: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )

    store: Mapped[Store] = relationship("Store")
    created_by: Mapped[User | None] = relationship("User")
    approved_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[approved_by_id]
    )
    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        "PurchaseOrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    returns: Mapped[list["PurchaseReturn"]] = relationship(
        "PurchaseReturn", back_populates="order", cascade="all, delete-orphan"
    )
    documents: Mapped[list["PurchaseOrderDocument"]] = relationship(
        "PurchaseOrderDocument",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="desc(PurchaseOrderDocument.uploaded_at)",
    )
    status_events: Mapped[list["PurchaseOrderStatusEvent"]] = relationship(
        "PurchaseOrderStatusEvent",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="PurchaseOrderStatusEvent.created_at",
    )


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    __table_args__ = (
        UniqueConstraint("purchase_order_id", "device_id",
                         name="uq_purchase_item_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_received: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0"))

    order: Mapped[PurchaseOrder] = relationship(
        "PurchaseOrder", back_populates="items")
    device: Mapped[Device] = relationship("Device")


class PurchaseReturn(Base):
    __tablename__ = "purchase_returns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    reason_category: Mapped[ReturnReasonCategory] = mapped_column(
        RETURN_REASON_CATEGORY_ENUM.copy(),
        nullable=False,
        default=ReturnReasonCategory.OTRO,
    )
    disposition: Mapped[ReturnDisposition] = mapped_column(
        RETURN_DISPOSITION_ENUM.copy(),
        nullable=False,
        default=ReturnDisposition.DEFECTUOSO,
    )
    warehouse_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    supplier_ledger_entry_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("supplier_ledger_entries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    corporate_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    credit_note_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    processed_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    approved_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)

    order: Mapped[PurchaseOrder] = relationship(
        "PurchaseOrder", back_populates="returns")
    device: Mapped[Device] = relationship("Device")
    ledger_entry: Mapped[SupplierLedgerEntry | None] = relationship(
        "SupplierLedgerEntry"
    )
    processed_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[processed_by_id]
    )
    approved_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[approved_by_id]
    )
    warehouse: Mapped[Warehouse | None] = relationship(
        "Warehouse", foreign_keys=[warehouse_id]
    )

    rma_requests: Mapped[list["RMARequest"]] = relationship(
        "RMARequest",
        back_populates="purchase_return",
        cascade="all, delete-orphan",
    )


class PurchaseOrderDocument(Base):
    __tablename__ = "purchase_order_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(80), nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(20), nullable=False)
    object_path: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    uploaded_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True
    )

    order: Mapped[PurchaseOrder] = relationship("PurchaseOrder", back_populates="documents")
    uploaded_by: Mapped[User | None] = relationship("User")


class PurchaseOrderStatusEvent(Base):
    __tablename__ = "purchase_order_status_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[PurchaseStatus] = mapped_column(
        Enum(PurchaseStatus, name="purchase_status"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    created_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True
    )

    order: Mapped[PurchaseOrder] = relationship(
        "PurchaseOrder", back_populates="status_events"
    )
    created_by: Mapped[User | None] = relationship("User")


class DTEStatus(str, enum.Enum):
    """Estados operativos de un documento tributario electrónico."""

    PENDIENTE = "PENDIENTE"
    EMITIDO = "EMITIDO"
    RECHAZADO = "RECHAZADO"
    ANULADO = "ANULADO"


class DTEDispatchStatus(str, enum.Enum):
    """Estados de la cola de envío de documentos tributarios."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


DTE_STATUS_ENUM = Enum(DTEStatus, name="dte_status")
DTEDISPATCH_STATUS_ENUM = Enum(DTEDispatchStatus, name="dte_dispatch_status")


class Sale(Base):
    __tablename__ = "ventas"

    id: Mapped[int] = mapped_column(
        "id_venta", Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[int | None] = mapped_column(
        "cliente_id",
        Integer,
        ForeignKey("clientes.id_cliente", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_name: Mapped[str | None] = mapped_column(
        String(120), nullable=True)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        "forma_pago",
        Enum(PaymentMethod, name="payment_method"),
        nullable=False,
        default=PaymentMethod.EFECTIVO,
    )
    discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0")
    )
    subtotal_amount: Mapped[Decimal] = mapped_column(
        "subtotal", Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        "impuesto", Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    total_amount: Mapped[Decimal] = mapped_column(
        "total", Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    loyalty_points_earned: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    loyalty_points_redeemed: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    status: Mapped[str] = mapped_column(
        "estado", String(30), nullable=False, default="COMPLETADA"
    )
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invoice_reported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    invoice_reported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    invoice_annulled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    invoice_credit_note_code: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        "fecha", DateTime(timezone=True), default=datetime.utcnow
    )
    dte_status: Mapped[DTEStatus] = mapped_column(
        DTE_STATUS_ENUM.copy(), nullable=False, default=DTEStatus.PENDIENTE
    )
    dte_reference: Mapped[str | None] = mapped_column(
        String(120), nullable=True, index=True
    )
    performed_by_id: Mapped[int | None] = mapped_column(
        "usuario_id",
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cash_session_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("cash_register_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    store: Mapped[Store] = relationship("Store")
    performed_by: Mapped[User | None] = relationship("User")
    customer: Mapped[Customer | None] = relationship(
        "Customer", back_populates="sales")
    cash_session: Mapped[CashRegisterSession | None] = relationship(
        "CashRegisterSession", back_populates="sales"
    )
    items: Mapped[list["SaleItem"]] = relationship(
        "SaleItem", back_populates="sale", cascade="all, delete-orphan"
    )
    returns: Mapped[list["SaleReturn"]] = relationship(
        "SaleReturn", back_populates="sale", cascade="all, delete-orphan"
    )
    store_credit_redemptions: Mapped[list["StoreCreditRedemption"]] = relationship(
        "StoreCreditRedemption",
        back_populates="sale",
        cascade="all, delete-orphan",
    )
    loyalty_transactions: Mapped[list["LoyaltyTransaction"]] = relationship(
        "LoyaltyTransaction",
        back_populates="sale",
        cascade="all, delete-orphan",
    )
    dte_documents: Mapped[list["DTEDocument"]] = relationship(
        "DTEDocument", back_populates="sale", cascade="all, delete-orphan"
    )


class SaleItem(Base):
    __tablename__ = "detalle_ventas"

    id: Mapped[int] = mapped_column(
        "id_detalle", Integer, primary_key=True, index=True)
    sale_id: Mapped[int] = mapped_column(
        "venta_id",
        Integer,
        ForeignKey("ventas.id_venta", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[int] = mapped_column(
        "producto_id",
        Integer,
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(
        "precio_unitario", Numeric(12, 2), nullable=False
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    total_line: Mapped[Decimal] = mapped_column(
        "subtotal", Numeric(12, 2), nullable=False
    )
    reservation_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("inventory_reservations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    warranty_status: Mapped[WarrantyStatus | None] = mapped_column(
        WARRANTY_STATUS_ENUM.copy(), nullable=True
    )

    sale: Mapped[Sale] = relationship("Sale", back_populates="items")
    device: Mapped[Device] = relationship("Device")
    reservation: Mapped["InventoryReservation | None"] = relationship(
        "InventoryReservation", back_populates="sale_items"
    )
    warranty_assignment: Mapped["WarrantyAssignment | None"] = relationship(
        "WarrantyAssignment", back_populates="sale_item", uselist=False
    )


class SaleReturn(Base):
    __tablename__ = "sale_returns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sale_id: Mapped[int] = mapped_column(
        "venta_id",
        Integer,
        ForeignKey("ventas.id_venta", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    reason_category: Mapped[ReturnReasonCategory] = mapped_column(
        RETURN_REASON_CATEGORY_ENUM.copy(),
        nullable=False,
        default=ReturnReasonCategory.OTRO,
    )
    disposition: Mapped[ReturnDisposition] = mapped_column(
        RETURN_DISPOSITION_ENUM.copy(),
        nullable=False,
        default=ReturnDisposition.VENDIBLE,
    )
    warehouse_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    processed_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    approved_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)

    sale: Mapped[Sale] = relationship("Sale", back_populates="returns")
    device: Mapped[Device] = relationship("Device")
    processed_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[processed_by_id]
    )
    approved_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[approved_by_id]
    )
    warehouse: Mapped[Warehouse | None] = relationship(
        "Warehouse", foreign_keys=[warehouse_id]
    )

    rma_requests: Mapped[list["RMARequest"]] = relationship(
        "RMARequest",
        back_populates="sale_return",
        cascade="all, delete-orphan",
    )


class WarrantyAssignment(Base):
    __tablename__ = "warranty_assignments"
    __table_args__ = (
        UniqueConstraint("sale_item_id", name="uq_warranty_sale_item"),
        Index("ix_warranty_assignments_device_id", "device_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sale_item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("detalle_ventas.id_detalle", ondelete="CASCADE"),
        nullable=False,
    )
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    coverage_months: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activation_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiration_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[WarrantyStatus] = mapped_column(
        WARRANTY_STATUS_ENUM.copy(), nullable=False, default=WarrantyStatus.ACTIVA
    )
    serial_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    activation_channel: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    sale_item: Mapped[SaleItem] = relationship(
        "SaleItem", back_populates="warranty_assignment"
    )
    device: Mapped[Device] = relationship("Device", back_populates="warranty_assignments")
    claims: Mapped[list["WarrantyClaim"]] = relationship(
        "WarrantyClaim", back_populates="assignment", cascade="all, delete-orphan"
    )


class RMARequest(Base):
    __tablename__ = "rma_requests"
    __table_args__ = (
        CheckConstraint(
            "(sale_return_id IS NOT NULL) <> (purchase_return_id IS NOT NULL)",
            name="ck_rma_single_return_reference",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sale_return_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sale_returns.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    purchase_return_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("purchase_returns.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    store_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    disposition: Mapped[ReturnDisposition] = mapped_column(
        RETURN_DISPOSITION_ENUM.copy(),
        nullable=False,
        default=ReturnDisposition.DEFECTUOSO,
    )
    status: Mapped[RMAStatus] = mapped_column(
        RMA_STATUS_ENUM.copy(), nullable=False, default=RMAStatus.PENDIENTE
    )
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    repair_order_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("repair_orders.id", ondelete="SET NULL"), nullable=True
    )
    replacement_sale_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("ventas.id_venta", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True
    )
    authorized_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True
    )
    processed_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True
    )
    closed_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    sale_return: Mapped[SaleReturn | None] = relationship(
        "SaleReturn", back_populates="rma_requests"
    )
    purchase_return: Mapped[PurchaseReturn | None] = relationship(
        "PurchaseReturn", back_populates="rma_requests"
    )
    store: Mapped[Store] = relationship("Store")
    device: Mapped[Device] = relationship("Device")
    repair_order: Mapped["RepairOrder | None"] = relationship("RepairOrder")
    replacement_sale: Mapped["Sale | None"] = relationship(
        "Sale", foreign_keys=[replacement_sale_id]
    )
    created_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[created_by_id]
    )
    authorized_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[authorized_by_id]
    )
    processed_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[processed_by_id]
    )
    closed_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[closed_by_id]
    )
    history: Mapped[list["RMAEvent"]] = relationship(
        "RMAEvent",
        back_populates="rma",
        cascade="all, delete-orphan",
        order_by="RMAEvent.created_at",
    )


class RMAEvent(Base):
    __tablename__ = "rma_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rma_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("rma_requests.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[RMAStatus] = mapped_column(RMA_STATUS_ENUM.copy(), nullable=False)
    message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    rma: Mapped[RMARequest] = relationship("RMARequest", back_populates="history")
    created_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[created_by_id]
    )


class WarrantyClaim(Base):
    __tablename__ = "warranty_claims"
    __table_args__ = (
        Index("ix_warranty_claim_assignment_id", "assignment_id"),
        Index("ix_warranty_claim_repair_order_id", "repair_order_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    assignment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("warranty_assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    claim_type: Mapped[WarrantyClaimType] = mapped_column(
        WARRANTY_CLAIM_TYPE_ENUM.copy(), nullable=False
    )
    status: Mapped[WarrantyClaimStatus] = mapped_column(
        WARRANTY_CLAIM_STATUS_ENUM.copy(), nullable=False, default=WarrantyClaimStatus.ABIERTO
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    performed_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
    )
    repair_order_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("repair_orders.id", ondelete="SET NULL"),
        nullable=True,
    )

    assignment: Mapped[WarrantyAssignment] = relationship(
        "WarrantyAssignment", back_populates="claims"
    )
    repair_order: Mapped["RepairOrder | None"] = relationship(
        "RepairOrder", back_populates="warranty_claims"
    )
    performed_by: Mapped[User | None] = relationship("User")


class RepairOrder(Base):
    __tablename__ = "repair_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("clientes.id_cliente", ondelete="SET NULL"), nullable=True, index=True
    )
    customer_name: Mapped[str | None] = mapped_column(
        String(120), nullable=True)
    customer_contact: Mapped[str | None] = mapped_column(
        String(120), nullable=True)  # // [PACK37-backend]
    technician_name: Mapped[str] = mapped_column(String(120), nullable=False)
    damage_type: Mapped[str] = mapped_column(String(120), nullable=False)
    diagnosis: Mapped[str | None] = mapped_column(
        Text, nullable=True)  # // [PACK37-backend]
    device_model: Mapped[str | None] = mapped_column(
        String(120), nullable=True)  # // [PACK37-backend]
    imei: Mapped[str | None] = mapped_column(
        String(40), nullable=True)  # // [PACK37-backend]
    device_description: Mapped[str | None] = mapped_column(
        String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[RepairStatus] = mapped_column(
        Enum(RepairStatus, name="repair_status"),
        nullable=False,
        default=RepairStatus.PENDIENTE,
    )
    labor_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    parts_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    total_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    parts_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    inventory_adjusted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    store: Mapped[Store] = relationship("Store")
    customer: Mapped[Customer | None] = relationship(
        "Customer", back_populates="repair_orders")
    parts: Mapped[list["RepairOrderPart"]] = relationship(
        "RepairOrderPart", back_populates="repair_order", cascade="all, delete-orphan"
    )
    warranty_claims: Mapped[list[WarrantyClaim]] = relationship(
        "WarrantyClaim", back_populates="repair_order"
    )


class RepairOrderPart(Base):
    __tablename__ = "repair_order_parts"
    __table_args__ = (
        UniqueConstraint(
            "repair_order_id",
            "device_id",
            "part_name",
            name="uq_repair_order_part",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    repair_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repair_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    part_name: Mapped[str | None] = mapped_column(
        String(120), nullable=True)  # // [PACK37-backend]
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    source: Mapped[RepairPartSource] = mapped_column(  # // [PACK37-backend]
        Enum(RepairPartSource, name="repair_part_source"),
        nullable=False,
        default=RepairPartSource.STOCK,
    )

    repair_order: Mapped[RepairOrder] = relationship(
        "RepairOrder", back_populates="parts")
    device: Mapped[Device | None] = relationship("Device")


class CashRegisterSession(Base):
    __tablename__ = "cash_register_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[CashSessionStatus] = mapped_column(
        Enum(CashSessionStatus, name="cash_session_status"),
        nullable=False,
        default=CashSessionStatus.ABIERTO,
    )
    opening_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    closing_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    expected_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    difference_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    payment_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict)
    denomination_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict)
    reconciliation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    difference_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    opened_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    closed_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    store: Mapped[Store] = relationship("Store")
    opened_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[opened_by_id], backref="cash_sessions_opened"
    )
    closed_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[closed_by_id], backref="cash_sessions_closed"
    )
    sales: Mapped[list[Sale]] = relationship(
        "Sale", back_populates="cash_session")
    entries: Mapped[list["CashRegisterEntry"]] = relationship(
        "CashRegisterEntry",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class CashRegisterEntry(Base):
    __tablename__ = "cash_register_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("cash_register_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_type: Mapped[CashEntryType] = mapped_column(
        Enum(CashEntryType, name="cash_entry_type"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    session: Mapped[CashRegisterSession] = relationship(
        "CashRegisterSession", back_populates="entries"
    )
    created_by: Mapped[User | None] = relationship("User")


class POSConfig(Base):
    __tablename__ = "pos_configs"

    store_id: Mapped[int] = mapped_column(
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0"))
    invoice_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    printer_name: Mapped[str | None] = mapped_column(
        String(120), nullable=True)
    printer_profile: Mapped[str | None] = mapped_column(
        String(255), nullable=True)
    quick_product_ids: Mapped[list[int]] = mapped_column(
        JSON, nullable=False, default=list)
    promotions_config: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    hardware_settings: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    store: Mapped[Store] = relationship("Store")


class POSDraftSale(Base):
    __tablename__ = "pos_draft_sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    store: Mapped[Store] = relationship("Store")


class UserTOTPSecret(Base):
    __tablename__ = "user_totp_secrets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False, unique=True
    )
    secret: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="totp_secret")


class ActiveSession(Base):
    __tablename__ = "active_sessions"
    __table_args__ = (UniqueConstraint(
        "session_token", name="uq_active_session_token"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False, index=True
    )
    session_token: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    revoked_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    revoke_reason: Mapped[str | None] = mapped_column(
        String(255), nullable=True)

    user: Mapped[User] = relationship(
        "User", foreign_keys=[user_id], back_populates="active_sessions"
    )
    revoked_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[revoked_by_id]
    )


class JWTBlacklist(Base):
    __tablename__ = "jwt_blacklist"
    __table_args__ = (UniqueConstraint("jti", name="uq_jwt_blacklist_jti"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    jti: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    token_type: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    revoked_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    revoked_by: Mapped[User | None] = relationship("User")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (UniqueConstraint(
        "token", name="uq_password_reset_token"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)

    user: Mapped[User] = relationship(
        "User", back_populates="password_reset_tokens")


class SyncOutbox(Base):
    __tablename__ = "sync_outbox"
    __table_args__ = (UniqueConstraint(
        "entity_type", "entity_id", name="uq_outbox_entity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(
        String(120), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(80), nullable=False)
    operation: Mapped[str] = mapped_column(String(40), nullable=False)
    _payload: Mapped[str] = mapped_column("payload", Text, nullable=False)
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    status: Mapped[SyncOutboxStatus] = mapped_column(
        Enum(SyncOutboxStatus, name="sync_outbox_status"),
        nullable=False,
        default=SyncOutboxStatus.PENDING,
    )
    priority: Mapped[SyncOutboxPriority] = mapped_column(
        Enum(SyncOutboxPriority, name="sync_outbox_priority"),
        nullable=False,
        default=SyncOutboxPriority.NORMAL,
    )
    error_message: Mapped[str | None] = mapped_column(
        String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    conflict_flag: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True)
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, index=True)

    def _get_payload(self) -> dict[str, Any]:
        raw = self._payload
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:  # pragma: no cover - datos corruptos
                return {}
        if raw is None:
            return {}
        try:
            return dict(raw)
        except TypeError:  # pragma: no cover - tolerar tipos no previstos
            return {}

    def _set_payload(self, value: dict[str, Any] | str | None) -> None:
        if value is None:
            self._payload = json.dumps({}, ensure_ascii=False)
            return
        if isinstance(value, str):
            self._payload = value
            return
        self._payload = json.dumps(value, ensure_ascii=False, default=str)

    payload = synonym(
        "_payload", descriptor=property(_get_payload, _set_payload)
    )

    @property
    def payload_raw(self) -> str:
        raw = self._payload
        if isinstance(raw, str):
            return raw
        return json.dumps(raw or {}, ensure_ascii=False, default=str)


# // [PACK35-backend]
class SyncQueueStatus(str, enum.Enum):
    """Estados posibles dentro de la cola híbrida de sincronización."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


# // [PACK35-backend]
class SyncQueue(Base):
    __tablename__ = "sync_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(
        String(120), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(120), nullable=True, unique=True)
    status: Mapped[SyncQueueStatus] = mapped_column(
        Enum(SyncQueueStatus, name="sync_queue_status"),
        nullable=False,
        default=SyncQueueStatus.PENDING,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    attempt_logs: Mapped[list["SyncAttempt"]] = relationship(
        "SyncAttempt",
        back_populates="queue_entry",
        cascade="all, delete-orphan",
    )


# // [PACK35-backend]
class SyncAttempt(Base):
    __tablename__ = "sync_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    queue_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sync_queue.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    success: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    queue_entry: Mapped[SyncQueue] = relationship(
        "SyncQueue", back_populates="attempt_logs")


class DTEAuthorization(Base):
    __tablename__ = "dte_authorizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    store_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    serie: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    range_start: Mapped[int] = mapped_column(Integer, nullable=False)
    range_end: Mapped[int] = mapped_column(Integer, nullable=False)
    current_number: Mapped[int] = mapped_column(Integer, nullable=False)
    cai: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    expiration_date: Mapped[date] = mapped_column(Date, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    store: Mapped[Store | None] = relationship("Store")
    documents: Mapped[list["DTEDocument"]] = relationship(
        "DTEDocument", back_populates="authorization", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "document_type",
            "serie",
            "store_id",
            name="uq_dte_authorization_scope",
        ),
    )


class DTEDocument(Base):
    __tablename__ = "dte_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sale_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ventas.id_venta", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    authorization_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("dte_authorizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    serie: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    correlative: Mapped[int] = mapped_column(Integer, nullable=False)
    control_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    cai: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    xml_content: Mapped[str] = mapped_column(Text, nullable=False)
    signature: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[DTEStatus] = mapped_column(
        DTE_STATUS_ENUM.copy(), nullable=False, default=DTEStatus.PENDIENTE
    )
    reference_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ack_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ack_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    sale: Mapped[Sale] = relationship("Sale", back_populates="dte_documents")
    authorization: Mapped[DTEAuthorization | None] = relationship(
        "DTEAuthorization", back_populates="documents"
    )
    events: Mapped[list["DTEEvent"]] = relationship(
        "DTEEvent", back_populates="document", cascade="all, delete-orphan"
    )
    dispatch_entries: Mapped[list["DTEDispatchQueue"]] = relationship(
        "DTEDispatchQueue", back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "serie",
            "correlative",
            name="uq_dte_documents_series_number",
        ),
    )


class DTEEvent(Base):
    __tablename__ = "dte_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("dte_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[DTEStatus] = mapped_column(
        DTE_STATUS_ENUM.copy(), nullable=False, default=DTEStatus.PENDIENTE
    )
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    performed_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    document: Mapped[DTEDocument] = relationship(
        "DTEDocument", back_populates="events"
    )
    performed_by: Mapped[User | None] = relationship("User")


class DTEDispatchQueue(Base):
    __tablename__ = "dte_dispatch_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("dte_documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[DTEDispatchStatus] = mapped_column(
        DTEDISPATCH_STATUS_ENUM.copy(),
        nullable=False,
        default=DTEDispatchStatus.PENDING,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    document: Mapped[DTEDocument] = relationship(
        "DTEDocument", back_populates="dispatch_entries"
    )


__all__ = [
    "CashRegisterSession",
    "CashSessionStatus",
    "CashEntryType",
    "CashRegisterEntry",
    "Customer", 
    "StoreCredit",
    "StoreCreditStatus",
    "StoreCreditRedemption",
    "AuditLog",
    "SystemLog",
    "SystemError",
    "SystemLogLevel",
    "FeedbackCategory",
    "FeedbackPriority",
    "FeedbackStatus",
    "SupportFeedback",
    "BackupJob",
    "BackupMode",
    "ActiveSession",
    "JWTBlacklist",
    "PasswordResetToken",
    "DeviceIdentifier",
    "Device",
    "PriceList",
    "PriceListItem",
    "InventoryMovement",
    "MovementType",
    "InventoryImportTemp",
    "ImportValidation",
    "PaymentMethod",
    "PurchaseOrder",
    "PurchaseOrderItem",
    "PurchaseOrderDocument",
    "PurchaseOrderStatusEvent",
    "PurchaseReturn",
    "PurchaseStatus",
    "SupplierLedgerEntry",
    "SupplierLedgerEntryType",
    "RepairOrder",
    "RepairOrderPart",
    "RepairStatus",
    "Role",
    "Store",
    "Warehouse",
    "SupplierBatch",
    "SyncMode",
    "SyncSession",
    "SyncStatus",
    "Supplier",
    "SyncOutbox",
    "SyncOutboxPriority",
    "SyncQueue",
    "SyncQueueStatus",
    "SyncAttempt",
    "TransferOrder",
    "TransferOrderItem",
    "TransferStatus",
    "UserTOTPSecret",
    "StoreMembership",
    "User",
    "UserRole",
    "Permission",
    "DTEStatus",
    "DTEDispatchStatus",
    "Sale",
    "SaleItem",
    "SaleReturn",
    "DTEAuthorization",
    "DTEDocument",
    "DTEEvent",
    "DTEDispatchQueue",
    "WarrantyAssignment",
    "WarrantyClaim",
    "WarrantyStatus",
    "WarrantyClaimStatus",
    "WarrantyClaimType",
    "POSConfig",
    "POSDraftSale",
    "RMARequest",
    "RMAEvent",
    "RMAStatus",
]
