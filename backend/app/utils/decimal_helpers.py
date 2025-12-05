"""Utilidades para operaciones con decimales, moneda y cálculos financieros."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def to_decimal(value: Decimal | float | int | None) -> Decimal:
    """Convierte un valor a Decimal de forma segura.
    
    Args:
        value: Valor a convertir (Decimal, float, int o None)
        
    Returns:
        Decimal equivalente (0 si value es None)
    """
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def quantize_currency(value: Decimal) -> Decimal:
    """Normaliza valores de moneda a dos decimales con redondeo estándar.
    
    Args:
        value: Valor decimal a normalizar
        
    Returns:
        Decimal redondeado a 2 decimales
    """
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def quantize_points(value: Decimal) -> Decimal:
    """Normaliza valores de puntos de lealtad con dos decimales.
    
    Args:
        value: Puntos a normalizar
        
    Returns:
        Decimal redondeado a 2 decimales
    """
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def quantize_rate(value: Decimal) -> Decimal:
    """Normaliza tasas de acumulación y canje a cuatro decimales.
    
    Args:
        value: Tasa a normalizar
        
    Returns:
        Decimal redondeado a 4 decimales
    """
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def format_currency(value: Decimal | float | int) -> str:
    """Formatea un valor como moneda con dos decimales.
    
    Args:
        value: Valor a formatear
        
    Returns:
        String formateado (ej: "1234.56")
    """
    normalized = quantize_currency(to_decimal(value))
    return f"{normalized:.2f}"


def calculate_weighted_average_cost(
    current_quantity: int,
    current_cost: Decimal,
    incoming_quantity: int,
    incoming_cost: Decimal,
) -> Decimal:
    """Calcula el costo promedio ponderado al recibir nuevo inventario.
    
    Args:
        current_quantity: Cantidad actual en inventario
        current_cost: Costo unitario actual
        incoming_quantity: Cantidad entrante
        incoming_cost: Costo unitario entrante
        
    Returns:
        Nuevo costo promedio ponderado
    """
    if incoming_quantity <= 0:
        return to_decimal(current_cost)
    existing_quantity = to_decimal(current_quantity)
    new_quantity = existing_quantity + to_decimal(incoming_quantity)
    if new_quantity <= Decimal("0"):
        return Decimal("0")
    existing_total = to_decimal(current_cost) * existing_quantity
    incoming_total = to_decimal(incoming_cost) * to_decimal(incoming_quantity)
    return (existing_total + incoming_total) / new_quantity
