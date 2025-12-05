"""Utilidades para gestión de caché del sistema."""
from typing import Any

def invalidate_inventory_movements_cache() -> None:
    """Invalida la caché de movimientos de inventario."""
    from ..crud_legacy import _INVENTORY_MOVEMENTS_CACHE
    _INVENTORY_MOVEMENTS_CACHE.clear()


def inventory_movements_report_cache_key(
    *,
    store_id: int | None,
    start: str | None,
    end: str | None,
    movement_type: str | None,
) -> str:
    """
    Genera clave de caché para reportes de movimientos de inventario.
    
    Args:
        store_id: ID de la tienda (None para todas)
        start: Fecha de inicio (formato ISO)
        end: Fecha de fin (formato ISO)
        movement_type: Tipo de movimiento (None para todos)
        
    Returns:
        Clave de caché única para esta combinación de parámetros
    """
    store_str = f"store={store_id}" if store_id else "store=all"
    start_str = f"start={start}" if start else "start=none"
    end_str = f"end={end}" if end else "end=none"
    type_str = f"type={movement_type}" if movement_type else "type=all"
    return f"inv_mov_report:{store_str}:{start_str}:{end_str}:{type_str}"


def persistent_alerts_cache_key(
    *,
    user_id: int | None,
    acknowledged_only: bool,
) -> str:
    """
    Genera clave de caché para alertas persistentes de auditoría.
    
    Args:
        user_id: ID de usuario (None para todos)
        acknowledged_only: Si True, solo alertas reconocidas
        
    Returns:
        Clave de caché única
    """
    user_str = f"user={user_id}" if user_id else "user=all"
    ack_str = "ack=yes" if acknowledged_only else "ack=no"
    return f"persistent_alerts:{user_str}:{ack_str}"


def invalidate_persistent_audit_alerts_cache() -> None:
    """Invalida la caché de alertas de auditoría persistentes."""
    from ..crud_legacy import _PERSISTENT_ALERTS_CACHE
    _PERSISTENT_ALERTS_CACHE.clear()
