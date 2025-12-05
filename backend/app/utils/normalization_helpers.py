"""Utilidades para normalización de datos generales."""
from __future__ import annotations

from collections.abc import Iterable


def normalize_store_ids(store_ids: Iterable[int] | None) -> set[int] | None:
    """Normaliza IDs de tiendas eliminando valores inválidos.
    
    Args:
        store_ids: Lista de IDs de tiendas
        
    Returns:
        Set de IDs válidos (>0) o None si no hay válidos
    """
    if not store_ids:
        return None
    normalized = {int(store_id) for store_id in store_ids if int(store_id) > 0}
    return normalized or None


def normalize_optional_note(note: str | None) -> str | None:
    """Normaliza una nota opcional eliminando espacios.
    
    Args:
        note: Nota a normalizar
        
    Returns:
        Nota normalizada o None si está vacía
    """
    if note is None:
        return None
    normalized = note.strip()
    return normalized or None


def normalize_movement_comment(comment: str | None) -> str:
    """Normaliza comentario de movimiento de inventario.
    
    Args:
        comment: Comentario a normalizar
        
    Returns:
        Comentario normalizado con mínimo de 5 caracteres
        
    Notas:
        - Si es None o vacío, usa "Movimiento inventario"
        - Si es < 5 caracteres, agrega " Kardex"
        - Trunca a 255 caracteres
    """
    if comment is None:
        normalized = "Movimiento inventario"
    else:
        normalized = comment.strip() or "Movimiento inventario"
    if len(normalized) < 5:
        normalized = f"{normalized} Kardex".strip()
    if len(normalized) < 5:
        normalized = "Movimiento inventario"
    return normalized[:255]


def normalize_role_names(role_names: Iterable[str]) -> list[str]:
    """Normaliza nombres de roles eliminando duplicados y vacíos.
    
    Args:
        role_names: Lista de nombres de roles
        
    Returns:
        Lista normalizada sin duplicados en minúsculas
    """
    normalized: list[str] = []
    for role in role_names:
        cleaned = str(role).strip().upper()
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def normalize_store_status(value: str | None) -> str:
    """Normaliza estado de tienda.
    
    Args:
        value: Estado a normalizar
        
    Returns:
        Estado normalizado (por defecto "activa")
    """
    normalized = (value or "activa").strip().lower()
    return normalized


def normalize_store_code(value: str | None) -> str | None:
    """Normaliza código de tienda.
    
    Args:
        value: Código a normalizar
        
    Returns:
        Código normalizado en mayúsculas o None
    """
    if not value:
        return None
    normalized = value.strip().upper()
    return normalized or None


def normalize_reservation_reason(reason: str | None) -> str:
    """Normaliza motivo de reserva.
    
    Args:
        reason: Motivo a normalizar
        
    Returns:
        Motivo normalizado (por defecto "Reserva cliente")
    """
    if not reason:
        return "Reserva cliente"
    normalized = reason.strip()
    return normalized or "Reserva cliente"
