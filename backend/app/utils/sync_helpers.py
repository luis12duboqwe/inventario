"""Utilidades para sistema de sincronización y mapeo de módulos."""
from __future__ import annotations

from .. import models

# Mapeo de prioridades por tipo de entidad
OUTBOX_PRIORITY_MAP: dict[str, models.SyncOutboxPriority] = {
    "sale": models.SyncOutboxPriority.HIGH,
    "transfer_order": models.SyncOutboxPriority.HIGH,
    "purchase_order": models.SyncOutboxPriority.NORMAL,
    "repair_order": models.SyncOutboxPriority.NORMAL,
    "customer": models.SyncOutboxPriority.NORMAL,
    "customer_privacy_request": models.SyncOutboxPriority.LOW,
    "customer_ledger_entry": models.SyncOutboxPriority.NORMAL,
    "supplier_ledger_entry": models.SyncOutboxPriority.NORMAL,
    "pos_config": models.SyncOutboxPriority.NORMAL,
    "supplier": models.SyncOutboxPriority.NORMAL,
    "cash_session": models.SyncOutboxPriority.NORMAL,
    "device": models.SyncOutboxPriority.NORMAL,
    "rma_request": models.SyncOutboxPriority.NORMAL,
    "inventory": models.SyncOutboxPriority.HIGH,
    "store": models.SyncOutboxPriority.LOW,
    "global": models.SyncOutboxPriority.LOW,
    "backup": models.SyncOutboxPriority.LOW,
    "pos_draft": models.SyncOutboxPriority.LOW,
}

# Orden de prioridades (menor = más prioritario)
OUTBOX_PRIORITY_ORDER: dict[models.SyncOutboxPriority, int] = {
    models.SyncOutboxPriority.HIGH: 0,
    models.SyncOutboxPriority.NORMAL: 1,
    models.SyncOutboxPriority.LOW: 2,
}

# Mapeo de tipos de entidad a módulos del sistema
SYSTEM_MODULE_MAP: dict[str, str] = {
    "sale": "ventas",
    "pos": "ventas",
    "purchase": "compras",
    "inventory": "inventario",
    "device": "inventario",
    "supplier_batch": "inventario",
    "inventory_adjustment": "ajustes",
    "adjustment": "ajustes",
    "backup": "respaldos",
    "config_parameter": "configuracion",
    "config_rate": "configuracion",
    "config_template": "configuracion",
    "config_sync": "configuracion",
    "user": "usuarios",
    "role": "usuarios",
    "auth": "usuarios",
    "sync_session": "sincronizacion",
    "store": "inventario",
    "pos_fiscal_print": "ventas",
    "customer": "clientes",
    "customer_privacy_request": "clientes",
    "supplier_ledger_entry": "proveedores",
    "supplier": "proveedores",
    "transfer_order": "inventario",
    "purchase_order": "compras",
    "purchase_vendor": "compras",
    "cash_session": "ventas",
}


def resolve_outbox_priority(
    entity_type: str, priority: models.SyncOutboxPriority | None
) -> models.SyncOutboxPriority:
    """Resuelve la prioridad de sincronización para un tipo de entidad.
    
    Args:
        entity_type: Tipo de entidad (sale, device, etc.)
        priority: Prioridad explícita (None para usar defaults)
        
    Returns:
        Prioridad de sincronización a usar
    """
    if priority is not None:
        return priority
    normalized = (entity_type or "").lower()
    return OUTBOX_PRIORITY_MAP.get(normalized, models.SyncOutboxPriority.NORMAL)


def priority_weight(priority: models.SyncOutboxPriority | None) -> int:
    """Convierte una prioridad a su peso numérico para ordenamiento.
    
    Args:
        priority: Prioridad de sincronización
        
    Returns:
        Peso numérico (menor = más prioritario)
    """
    if priority is None:
        return OUTBOX_PRIORITY_ORDER[models.SyncOutboxPriority.NORMAL]
    return OUTBOX_PRIORITY_ORDER.get(priority, 1)


def resolve_system_module(entity_type: str) -> str:
    """Resuelve el módulo del sistema al que pertenece un tipo de entidad.
    
    Args:
        entity_type: Tipo de entidad
        
    Returns:
        Nombre del módulo del sistema (ventas, inventario, etc.)
        
    Notas:
        Busca el prefijo más largo que coincida para mejor precisión.
        Retorna "general" si no encuentra coincidencia.
    """
    normalized = (entity_type or "").lower()
    for prefix, module in sorted(
        SYSTEM_MODULE_MAP.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if normalized.startswith(prefix):
            return module
    return "general"


def map_system_level(action: str, details: str | None) -> models.SystemLogLevel:
    """Mapea una acción de auditoría a un nivel de sistema de logs.
    
    Args:
        action: Acción realizada
        details: Detalles de la acción
        
    Returns:
        Nivel de sistema de logs (INFO, WARNING, CRITICAL)
    """
    # Import here to avoid circular dependency
    from ..utils import audit as audit_utils
    
    severity = audit_utils.classify_severity(action or "", details)
    if severity == "critical":
        return models.SystemLogLevel.CRITICAL
    if severity == "warning":
        return models.SystemLogLevel.WARNING
    return models.SystemLogLevel.INFO
