"""Rutinas de auditoría para validar la integridad del inventario."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas


def _to_decimal(value: Decimal | float | int | None) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _simulate_device_inventory(
    movements: list[models.InventoryMovement],
) -> tuple[int, Decimal, list[str], int | None, datetime | None]:
    quantity = 0
    average_cost = Decimal("0")
    issues: list[str] = []
    last_movement_id: int | None = None
    last_movement_date: datetime | None = None

    ordered_movements = sorted(
        movements,
        key=lambda movement: (
            movement.created_at or datetime.min,
            movement.id or 0,
        ),
    )

    for movement in ordered_movements:
        last_movement_id = movement.id
        last_movement_date = movement.created_at
        if movement.movement_type == models.MovementType.IN:
            incoming_cost = (
                _to_decimal(movement.unit_cost)
                if movement.unit_cost is not None
                else average_cost
            )
            previous_total = average_cost * Decimal(quantity)
            updated_total = previous_total + incoming_cost * Decimal(movement.quantity)
            quantity += movement.quantity
            if quantity > 0:
                average_cost = (updated_total / Decimal(quantity)).quantize(
                    Decimal("0.0001"), rounding=ROUND_HALF_UP
                )
            else:
                average_cost = Decimal("0")
        elif movement.movement_type == models.MovementType.OUT:
            quantity -= movement.quantity
            if quantity < 0:
                issues.append("stock_negativo")
            if quantity <= 0:
                average_cost = Decimal("0")
        elif movement.movement_type == models.MovementType.ADJUST:
            quantity = movement.quantity
            if movement.unit_cost is not None and quantity > 0:
                average_cost = _to_decimal(movement.unit_cost)
            elif quantity <= 0:
                average_cost = Decimal("0")
        else:
            issues.append("tipo_movimiento_desconocido")

    return quantity, average_cost, issues, last_movement_id, last_movement_date


def build_inventory_integrity_report(
    db: Session, *, store_ids: Iterable[int] | None = None
) -> schemas.InventoryIntegrityReport:
    """Calcula un resumen de integridad entre existencias y movimientos."""

    device_stmt = (
        select(models.Device)
        .options(joinedload(models.Device.store), joinedload(models.Device.movements))
        .order_by(models.Device.store_id.asc(), models.Device.id.asc())
    )
    if store_ids:
        normalized = sorted({int(store_id) for store_id in store_ids if int(store_id) > 0})
        if normalized:
            device_stmt = device_stmt.where(models.Device.store_id.in_(normalized))

    devices = list(db.scalars(device_stmt).unique())

    statuses: list[schemas.InventoryIntegrityDeviceStatus] = []
    inconsistent_devices = 0
    discrepancy_count = 0

    for device in devices:
        movements = list(device.movements)
        if not movements and device.quantity <= 0:
            continue

        expected_quantity, expected_cost, base_issues, last_id, last_date = (
            _simulate_device_inventory(movements)
        )
        issues = list(base_issues)
        discrepancy_count += len(base_issues)

        actual_quantity = device.quantity
        actual_cost = _to_decimal(device.costo_unitario)

        if not movements and actual_quantity > 0:
            issues.append("sin_movimientos")
            discrepancy_count += 1

        if expected_quantity != actual_quantity:
            issues.append("diferencia_existencias")
            discrepancy_count += 1

        if actual_quantity > 0:
            expected_cost_rounded = expected_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            actual_cost_rounded = actual_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if expected_cost_rounded != actual_cost_rounded:
                issues.append("diferencia_costo_promedio")
                discrepancy_count += 1
        elif actual_cost != Decimal("0"):
            issues.append("costo_inconsistente")
            discrepancy_count += 1

        if not issues:
            continue

        inconsistent_devices += 1
        statuses.append(
            schemas.InventoryIntegrityDeviceStatus(
                store_id=device.store_id,
                store_name=device.store.name if device.store else None,
                device_id=device.id,
                sku=device.sku,
                quantity_actual=actual_quantity,
                quantity_calculada=expected_quantity,
                costo_actual=actual_cost,
                costo_calculado=expected_cost,
                last_movement_id=last_id,
                last_movement_fecha=last_date,
                issues=issues,
            )
        )

    summary = schemas.InventoryIntegritySummary(
        dispositivos_evaluados=len(devices),
        dispositivos_inconsistentes=inconsistent_devices,
        discrepancias_totales=discrepancy_count,
    )
    return schemas.InventoryIntegrityReport(resumen=summary, dispositivos=statuses)
