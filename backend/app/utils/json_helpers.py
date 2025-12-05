"""Utilidades para manejo de datos JSON y transformaciones de estructuras."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from .. import schemas


def merge_defaults(default: object, provided: object) -> object:
    """Fusiona recursivamente configuraciones con valores por defecto.
    
    Args:
        default: Configuración por defecto
        provided: Configuración proporcionada
        
    Returns:
        Configuración fusionada (provided sobrescribe default)
        
    Notas:
        - Fusiona diccionarios recursivamente
        - Listas completas se reemplazan (no se fusionan)
        - None en provided mantiene el default
    """
    if isinstance(default, dict) and isinstance(provided, dict):
        merged: dict[str, object] = {
            key: merge_defaults(value, provided.get(key))
            for key, value in default.items()
        }
        for key, value in provided.items():
            if key not in merged:
                merged[key] = value
            elif isinstance(value, (dict, list)):
                merged[key] = merge_defaults(merged[key], value)
            elif value is not None:
                merged[key] = value
        return merged
    if isinstance(default, list) and isinstance(provided, list):
        return provided or default
    return provided if provided is not None else default


def normalize_hardware_settings(
    raw: dict[str, object] | None,
) -> dict[str, object]:
    """Normaliza configuración de hardware POS con valores por defecto.
    
    Args:
        raw: Configuración cruda de hardware
        
    Returns:
        Configuración normalizada con defaults aplicados
    """
    default_settings = schemas.POSHardwareSettings().model_dump()
    if not raw:
        return default_settings
    return merge_defaults(default_settings, raw)


def history_to_json(
    entries: list[schemas.ContactHistoryEntry] | list[dict[str, object]] | None,
) -> list[dict[str, object]]:
    """Normaliza entradas de historial a formato JSON consistente.
    
    Args:
        entries: Historial de contacto (schemas o dicts)
        
    Returns:
        Lista de dicts con timestamp (ISO) y note
    """
    normalized: list[dict[str, object]] = []
    if not entries:
        return normalized
    for entry in entries:
        if isinstance(entry, schemas.ContactHistoryEntry):
            timestamp = entry.timestamp
            note = entry.note
        else:
            timestamp = entry.get("timestamp")  # type: ignore[assignment]
            note = entry.get("note") if isinstance(entry, dict) else None
        if isinstance(timestamp, str):
            parsed_timestamp = timestamp
        elif isinstance(timestamp, datetime):
            parsed_timestamp = timestamp.isoformat()
        else:
            parsed_timestamp = datetime.now(timezone.utc).isoformat()
        normalized.append({
            "timestamp": parsed_timestamp,
            "note": (note or "").strip()
        })
    return normalized


def contacts_to_json(
    contacts: list[schemas.SupplierContact] | list[dict[str, object]] | None,
) -> list[dict[str, object]]:
    """Normaliza contactos de proveedor a formato JSON.
    
    Args:
        contacts: Lista de contactos (schemas o dicts)
        
    Returns:
        Lista de dicts normalizados con campos: name, position, email, phone, notes
    """
    normalized: list[dict[str, object]] = []
    if not contacts:
        return normalized
    for contact in contacts:
        if isinstance(contact, schemas.SupplierContact):
            payload = contact.model_dump(exclude_none=True)
        elif isinstance(contact, Mapping):
            payload = {
                key: value
                for key, value in contact.items()
                if isinstance(key, str)
            }
        else:
            continue
        record: dict[str, object] = {}
        for key in ("name", "position", "email", "phone", "notes"):
            value = payload.get(key)
            if isinstance(value, str):
                value = value.strip()
            if value:
                record[key] = value
        if record:
            normalized.append(record)
    return normalized


def products_to_json(products: Sequence[str] | None) -> list[str]:
    """Normaliza lista de productos eliminando duplicados y vacíos.
    
    Args:
        products: Lista de nombres/IDs de productos
        
    Returns:
        Lista normalizada sin duplicados ni valores vacíos
    """
    if not products:
        return []
    normalized: list[str] = []
    for product in products:
        text = (product or "").strip()
        if not text:
            continue
        if text not in normalized:
            normalized.append(text)
    return normalized


def last_history_timestamp(history: list[dict[str, object]]) -> datetime | None:
    """Obtiene el timestamp más reciente de un historial.
    
    Args:
        history: Lista de entradas de historial con campo timestamp
        
    Returns:
        Datetime más reciente o None si no hay timestamps válidos
    """
    timestamps = []
    for entry in history:
        raw_timestamp = entry.get("timestamp")
        if isinstance(raw_timestamp, datetime):
            timestamps.append(raw_timestamp)
        elif isinstance(raw_timestamp, str):
            try:
                timestamps.append(datetime.fromisoformat(raw_timestamp))
            except ValueError:
                continue
    if not timestamps:
        return None
    return max(timestamps)


def append_customer_history(customer: Any, note: str) -> None:
    """Agrega una entrada al historial de un cliente.
    
    Args:
        customer: Objeto cliente con atributos history y last_interaction_at
        note: Nota a agregar
        
    Notas:
        Modifica el objeto customer in-place
    """
    history = list(customer.history or [])
    history.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "note": note
    })
    customer.history = history
    customer.last_interaction_at = datetime.now(timezone.utc)
