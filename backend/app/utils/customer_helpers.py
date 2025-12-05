"""Utilidades para normalización y validación de datos de clientes."""
from __future__ import annotations

import re
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.exc import IntegrityError

from .. import models
from .decimal_helpers import to_decimal

# Constantes de validación
ALLOWED_CUSTOMER_STATUSES = {
    "activo", "inactivo", "moroso", "vip", "bloqueado"
}
ALLOWED_CUSTOMER_TYPES = {"minorista", "mayorista", "corporativo"}
RTN_CANONICAL_TEMPLATE = "{0}-{1}-{2}"


def normalize_customer_status(value: str | None) -> str:
    """Normaliza y valida el estado de un cliente.
    
    Args:
        value: Estado a normalizar (None usa "activo" por defecto)
        
    Returns:
        Estado normalizado
        
    Raises:
        ValueError: Si el estado no es válido
    """
    normalized = (value or "activo").strip().lower()
    if normalized not in ALLOWED_CUSTOMER_STATUSES:
        raise ValueError("invalid_customer_status")
    return normalized


def normalize_customer_type(value: str | None) -> str:
    """Normaliza y valida el tipo de cliente.
    
    Args:
        value: Tipo a normalizar (None usa "minorista" por defecto)
        
    Returns:
        Tipo normalizado
        
    Raises:
        ValueError: Si el tipo no es válido
    """
    normalized = (value or "minorista").strip().lower()
    if normalized not in ALLOWED_CUSTOMER_TYPES:
        raise ValueError("invalid_customer_type")
    return normalized


def normalize_customer_segment_category(value: str | None) -> str | None:
    """Normaliza la categoría de segmento de un cliente.
    
    Args:
        value: Categoría a normalizar
        
    Returns:
        Categoría normalizada o None si está vacía
    """
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def normalize_customer_tags(tags: Sequence[str] | None) -> list[str]:
    """Normaliza etiquetas de cliente eliminando duplicados y valores vacíos.
    
    Args:
        tags: Lista de etiquetas
        
    Returns:
        Lista normalizada sin duplicados
    """
    if not tags:
        return []
    normalized: list[str] = []
    for tag in tags:
        if not isinstance(tag, str):
            continue
        cleaned = tag.strip().lower()
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def normalize_rtn(value: str | None, *, error_code: str) -> str:
    """Normaliza un RTN (Registro Tributario Nacional) a formato canónico.
    
    Args:
        value: RTN a normalizar
        error_code: Código de error a lanzar si es inválido
        
    Returns:
        RTN en formato XXXX-XXXX-XXXXXX
        
    Raises:
        ValueError: Si el RTN no tiene exactamente 14 dígitos
    """
    digits = re.sub(r"[^0-9]", "", value or "")
    if len(digits) != 14:
        raise ValueError(error_code)
    return RTN_CANONICAL_TEMPLATE.format(digits[:4], digits[4:8], digits[8:])


def generate_customer_tax_id_placeholder() -> str:
    """Genera un RTN placeholder único para clientes.
    
    Returns:
        RTN placeholder en formato canónico
    """
    placeholder = models.generate_customer_tax_id_placeholder()
    return normalize_rtn(placeholder, error_code="customer_tax_id_invalid")


def normalize_customer_tax_id(
    value: str | None, *, allow_placeholder: bool = True
) -> str:
    """Normaliza el RTN de un cliente.
    
    Args:
        value: RTN a normalizar
        allow_placeholder: Si True, genera un placeholder si value está vacío
        
    Returns:
        RTN normalizado o placeholder
        
    Raises:
        ValueError: Si el RTN es inválido y no se permite placeholder
    """
    cleaned = (value or "").strip()
    if cleaned:
        return normalize_rtn(cleaned, error_code="customer_tax_id_invalid")
    if allow_placeholder:
        return generate_customer_tax_id_placeholder()
    raise ValueError("customer_tax_id_invalid")


def is_tax_id_integrity_error(error: IntegrityError) -> bool:
    """Verifica si un error de integridad está relacionado con tax_id.
    
    Args:
        error: Error de integridad de SQLAlchemy
        
    Returns:
        True si el error está relacionado con tax_id/rtn
    """
    message = str(getattr(error, "orig", error)).lower()
    return "rtn" in message or "tax_id" in message or "segmento_etiquetas" in message


def ensure_non_negative_decimal(value: Decimal, error_code: str) -> Decimal:
    """Valida que un decimal sea no-negativo.
    
    Args:
        value: Valor a validar
        error_code: Código de error a lanzar si es negativo
        
    Returns:
        Decimal normalizado y validado
        
    Raises:
        ValueError: Si el valor es negativo
    """
    normalized = to_decimal(value).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)
    if normalized < Decimal("0"):
        raise ValueError(error_code)
    return normalized


def ensure_positive_decimal(value: Decimal, error_code: str) -> Decimal:
    """Valida que un decimal sea positivo.
    
    Args:
        value: Valor a validar
        error_code: Código de error a lanzar si no es positivo
        
    Returns:
        Decimal normalizado y validado
        
    Raises:
        ValueError: Si el valor es <= 0
    """
    normalized = to_decimal(value).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if normalized <= Decimal("0"):
        raise ValueError(error_code)
    return normalized


def ensure_discount_percentage(
    value: Decimal | None, error_code: str
) -> Decimal | None:
    """Valida que un porcentaje de descuento esté en rango válido (0-100).
    
    Args:
        value: Porcentaje a validar (None es permitido)
        error_code: Código de error a lanzar si está fuera de rango
        
    Returns:
        Decimal normalizado o None
        
    Raises:
        ValueError: Si el valor está fuera del rango 0-100
    """
    if value is None:
        return None
    normalized = to_decimal(value).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if normalized < Decimal("0") or normalized > Decimal("100"):
        raise ValueError(error_code)
    return normalized
