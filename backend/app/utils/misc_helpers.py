"""Utilidades misceláneas y helpers generales."""
from __future__ import annotations


def get_supplier_by_name(
    db: any, supplier_name: str | None
) -> any:
    """Busca un proveedor por nombre (case-insensitive)."""
    if not supplier_name:
        return None
    from sqlalchemy import func, select
    from .. import models
    normalized = supplier_name.strip().lower()
    if not normalized:
        return None
    statement = (
        select(models.Supplier)
        .where(func.lower(models.Supplier.name) == normalized)
        .limit(1)
    )
    return db.scalars(statement).first()


def recalculate_sale_price(device: any) -> None:
    """Recalcula precio de venta basado en costo y margen."""
    from decimal import ROUND_HALF_UP, Decimal
    from .decimal_helpers import to_decimal
    base_cost = to_decimal(device.costo_unitario)
    margin = to_decimal(device.margen_porcentaje)
    sale_factor = Decimal("1") + (margin / Decimal("100"))
    recalculated = (
        base_cost * sale_factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    device.unit_price = recalculated
    device.precio_venta = recalculated


def severity_weight(level: any) -> int:
    """Convierte nivel de log a peso numérico para ordenamiento."""
    from .. import models
    if level == models.SystemLogLevel.CRITICAL:
        return 3
    if level == models.SystemLogLevel.ERROR:
        return 2
    if level == models.SystemLogLevel.WARNING:
        return 1
    return 0
