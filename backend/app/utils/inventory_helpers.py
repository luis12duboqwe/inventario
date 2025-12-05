"""Utilidades para cálculos de inventario y valoración."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import ColumnElement

from .. import models
from .decimal_helpers import to_decimal


def device_value(device: models.Device) -> Decimal:
    """Calcula el valor monetario total de un dispositivo.
    
    Args:
        device: Dispositivo a valorar
        
    Returns:
        Valor total (quantity * unit_price)
    """
    return Decimal(device.quantity) * (device.unit_price or Decimal("0"))


def movement_value(movement: models.InventoryMovement) -> Decimal:
    """Calcula el valor monetario estimado de un movimiento de inventario.
    
    Args:
        movement: Movimiento de inventario
        
    Returns:
        Valor del movimiento (quantity * unit_cost)
        
    Notas:
        Si el movimiento no tiene unit_cost, intenta usar el costo del dispositivo
        o en su defecto el precio de venta.
    """
    unit_cost: Decimal | None = movement.unit_cost
    if unit_cost is None and movement.device is not None:
        if getattr(movement.device, "costo_unitario", None):
            unit_cost = movement.device.costo_unitario
        elif movement.device.unit_price is not None:
            unit_cost = movement.device.unit_price
    base_cost = to_decimal(unit_cost)
    return (Decimal(movement.quantity) * base_cost).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def device_category_expr() -> ColumnElement[str]:
    """Genera una expresión SQL para obtener la categoría de un dispositivo.
    
    Returns:
        Expresión que devuelve modelo, SKU o nombre (en ese orden de prioridad)
    """
    return func.coalesce(
        func.nullif(models.Device.modelo, ""),
        func.nullif(models.Device.sku, ""),
        func.nullif(models.Device.name, ""),
    )


def recalculate_store_inventory_value(
    db: Session, store: models.Store | int
) -> Decimal:
    """Recalcula y actualiza el valor total del inventario de una tienda.
    
    Args:
        db: Sesión de base de datos
        store: Tienda (modelo o ID)
        
    Returns:
        Nuevo valor total del inventario
        
    Notas:
        Actualiza el campo inventory_value de la tienda y hace flush.
    """
    # Import here to avoid circular dependency
    from ..crud_legacy import get_store, flush_session
    
    if isinstance(store, models.Store):
        store_obj = store
    else:
        store_obj = get_store(db, int(store))
    
    flush_session(db)
    
    total_value = db.scalar(
        select(func.coalesce(
            func.sum(models.Device.quantity * models.Device.unit_price), 0))
        .where(models.Device.store_id == store_obj.id)
    )
    
    normalized_total = to_decimal(total_value).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    
    store_obj.inventory_value = normalized_total
    db.add(store_obj)
    flush_session(db)
    
    return normalized_total
