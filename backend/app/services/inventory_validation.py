"""Validaciones de inventario y dispositivos."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import models


def ensure_unique_identifiers(
    db: Session,
    *,
    imei: str | None,
    serial: str | None,
    exclude_device_id: int | None = None,
) -> None:
    """Verifica que IMEI y número de serie sean únicos.
    
    Args:
        db: Sesión de base de datos
        imei: IMEI a validar
        serial: Número de serie a validar
        exclude_device_id: ID de dispositivo a excluir de la validación
        
    Raises:
        ValueError: Si se encuentra un conflicto con "device_identifier_conflict"
    """
    if imei:
        statement = select(models.Device).where(models.Device.imei == imei)
        if exclude_device_id:
            statement = statement.where(models.Device.id != exclude_device_id)
        if db.scalars(statement).first() is not None:
            raise ValueError("device_identifier_conflict")
        identifier_statement = select(models.DeviceIdentifier).where(
            or_(
                models.DeviceIdentifier.imei_1 == imei,
                models.DeviceIdentifier.imei_2 == imei,
            )
        )
        if exclude_device_id:
            identifier_statement = identifier_statement.where(
                models.DeviceIdentifier.producto_id != exclude_device_id
            )
        if db.scalars(identifier_statement).first() is not None:
            raise ValueError("device_identifier_conflict")
    if serial:
        statement = select(models.Device).where(models.Device.serial == serial)
        if exclude_device_id:
            statement = statement.where(models.Device.id != exclude_device_id)
        if db.scalars(statement).first() is not None:
            raise ValueError("device_identifier_conflict")
        identifier_statement = select(models.DeviceIdentifier).where(
            models.DeviceIdentifier.numero_serie == serial
        )
        if exclude_device_id:
            identifier_statement = identifier_statement.where(
                models.DeviceIdentifier.producto_id != exclude_device_id
            )
        if db.scalars(identifier_statement).first() is not None:
            raise ValueError("device_identifier_conflict")


def ensure_unique_identifier_payload(
    db: Session,
    *,
    imei_1: str | None,
    imei_2: str | None,
    numero_serie: str | None,
    exclude_device_id: int | None = None,
    exclude_identifier_id: int | None = None,
) -> None:
    """Verifica que los identificadores de un payload sean únicos.
    
    Args:
        db: Sesión de base de datos
        imei_1: Primer IMEI a validar
        imei_2: Segundo IMEI a validar
        numero_serie: Número de serie a validar
        exclude_device_id: ID de dispositivo a excluir
        exclude_identifier_id: ID de identificador a excluir
        
    Raises:
        ValueError: Si se encuentra un conflicto con "device_identifier_conflict"
    """
    imei_values = {value for value in (imei_1, imei_2) if value}
    for imei in imei_values:
        statement = select(models.Device).where(models.Device.imei == imei)
        if exclude_device_id:
            statement = statement.where(models.Device.id != exclude_device_id)
        if db.scalars(statement).first() is not None:
            raise ValueError("device_identifier_conflict")

        identifier_statement = select(models.DeviceIdentifier).where(
            or_(
                models.DeviceIdentifier.imei_1 == imei,
                models.DeviceIdentifier.imei_2 == imei,
            )
        )
        if exclude_device_id:
            identifier_statement = identifier_statement.where(
                models.DeviceIdentifier.producto_id != exclude_device_id
            )
        if exclude_identifier_id:
            identifier_statement = identifier_statement.where(
                models.DeviceIdentifier.id != exclude_identifier_id
            )
        if db.scalars(identifier_statement).first() is not None:
            raise ValueError("device_identifier_conflict")

    if numero_serie:
        statement = select(models.Device).where(
            models.Device.serial == numero_serie)
        if exclude_device_id:
            statement = statement.where(models.Device.id != exclude_device_id)
        if db.scalars(statement).first() is not None:
            raise ValueError("device_identifier_conflict")

        identifier_statement = select(models.DeviceIdentifier).where(
            models.DeviceIdentifier.numero_serie == numero_serie
        )
        if exclude_device_id:
            identifier_statement = identifier_statement.where(
                models.DeviceIdentifier.producto_id != exclude_device_id
            )
        if exclude_identifier_id:
            identifier_statement = identifier_statement.where(
                models.DeviceIdentifier.id != exclude_identifier_id
            )
        if db.scalars(identifier_statement).first() is not None:
            raise ValueError("device_identifier_conflict")


def validate_device_numeric_fields(values: dict[str, Any]) -> None:
    """Valida que los campos numéricos de un dispositivo sean válidos.
    
    Args:
        values: Diccionario con los valores a validar
        
    Raises:
        ValueError: Si quantity o costo_unitario son inválidos
    """
    quantity = values.get("quantity")
    if quantity is not None:
        try:
            parsed_quantity = int(quantity)
        except (TypeError, ValueError):
            raise ValueError("device_invalid_quantity")
        if parsed_quantity < 0:
            raise ValueError("device_invalid_quantity")

    raw_cost = values.get("costo_unitario")
    if raw_cost is not None:
        try:
            parsed_cost = _to_decimal(raw_cost)
        except (ArithmeticError, TypeError, ValueError):
            raise ValueError("device_invalid_cost")
        if parsed_cost < 0:
            raise ValueError("device_invalid_cost")


def _to_decimal(value: Decimal | float | int | None) -> Decimal:
    """Convierte un valor a Decimal de forma segura.
    
    Args:
        value: Valor a convertir
        
    Returns:
        Decimal equivalente
    """
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
