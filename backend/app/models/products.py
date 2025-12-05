from __future__ import annotations
import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.sql import column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .stores import Store, Warehouse
    from .inventory import InventoryMovement, InventoryReservation, ImportValidation
    from .sales import PriceListItem, WarrantyAssignment


class CommercialState(str, enum.Enum):
    """Clasificación comercial del dispositivo en catálogo pro."""

    NUEVO = "nuevo"
    A = "A"
    B = "B"
    C = "C"


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("sucursal_id", "warehouse_id", "sku",
                         name="uq_devices_store_warehouse_sku"),
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
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false")
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    store: Mapped[Store] = relationship("Store", back_populates="devices")
    warehouse: Mapped[Warehouse | None] = relationship(
        "Warehouse", back_populates="devices")
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
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    device: Mapped["Device"] = relationship(
        "Device", back_populates="variants")
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
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    store: Mapped[Optional[Store]] = relationship(
        "Store", back_populates="bundles")
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
    device: Mapped["Device"] = relationship(
        "Device", back_populates="bundle_items")
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

    device: Mapped["Device"] = relationship(
        "Device", back_populates="identifier")
