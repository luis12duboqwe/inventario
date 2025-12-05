"""Servicios auxiliares para costeo contable de inventario."""
from __future__ import annotations

from collections import deque
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Deque

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from .. import models

_ZERO = Decimal("0")
_FOUR_PLACES = Decimal("0.0001")
_TWO_PLACES = Decimal("0.01")


def _to_decimal(value: Decimal | int | float | None) -> Decimal:
    if value is None:
        return _ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _resolve_method(method: str | models.CostingMethod | None) -> models.CostingMethod:
    if isinstance(method, models.CostingMethod):
        return method
    if isinstance(method, str):
        normalized = method.strip().upper()
        if normalized in {m.value for m in models.CostingMethod}:
            return models.CostingMethod(normalized)
    return models.CostingMethod(settings.cost_method)


def _consume_lots(lots: Deque[list[Decimal]], quantity: Decimal) -> None:
    remaining = quantity
    while lots and remaining > _ZERO:
        lot_quantity, lot_cost = lots[0]
        if lot_quantity <= remaining:
            remaining -= lot_quantity
            lots.popleft()
        else:
            lots[0][0] = (lot_quantity - remaining).quantize(_FOUR_PLACES)
            remaining = _ZERO


def _current_average_cost(db: Session, product_id: int) -> Decimal:
    device_stmt = select(models.Device.costo_unitario).where(
        models.Device.id == product_id)
    device_cost = db.scalar(device_stmt)
    return _to_decimal(device_cost or _ZERO)


def record_move(
    db: Session,
    *,
    product_id: int,
    branch_id: int | None,
    quantity: Decimal | int | float,
    move_type: models.StockMoveType,
    reference: str | None = None,
    occurred_at: datetime | None = None,
) -> models.StockMove:
    """Crea un registro de `stock_moves` asociado a un movimiento de inventario."""  # // [PACK30-31-BACKEND]

    timestamp = occurred_at or datetime.utcnow()
    normalized_reference = reference.strip() if isinstance(reference, str) else None
    normalized_quantity = _to_decimal(quantity).quantize(_FOUR_PLACES)
    move = models.StockMove(
        product_id=product_id,
        branch_id=branch_id,
        quantity=normalized_quantity,
        movement_type=move_type,
        reference=normalized_reference,
        timestamp=timestamp,
    )
    db.add(move)
    db.flush()
    db.refresh(move)
    return move


def _simulate_fifo_cost(
    db: Session,
    *,
    product_id: int,
    branch_id: int,
    quantity: Decimal,
) -> Decimal:
    lots: Deque[list[Decimal]] = deque()
    current_stock = _ZERO
    last_known_cost = _current_average_cost(db, product_id)

    movement_stmt = (
        select(models.InventoryMovement)
        .where(
            models.InventoryMovement.device_id == product_id,
            models.InventoryMovement.store_id == branch_id,
        )
        .order_by(models.InventoryMovement.created_at.asc(), models.InventoryMovement.id.asc())
    )
    for movement in db.scalars(movement_stmt).unique():
        move_quantity = _to_decimal(movement.quantity).quantize(_FOUR_PLACES)
        move_cost = _to_decimal(movement.unit_cost).quantize(_TWO_PLACES)
        if movement.movement_type == models.MovementType.IN:
            lots.append([move_quantity, move_cost if move_cost >
                        _ZERO else last_known_cost])
            current_stock += move_quantity
            if move_cost > _ZERO:
                last_known_cost = move_cost
        elif movement.movement_type == models.MovementType.OUT:
            current_stock = max(_ZERO, current_stock - move_quantity)
            _consume_lots(lots, move_quantity)
        elif movement.movement_type == models.MovementType.ADJUST:
            target_quantity = move_quantity
            if target_quantity < current_stock:
                _consume_lots(lots, current_stock - target_quantity)
            elif target_quantity > current_stock:
                added = target_quantity - current_stock
                additional_cost = move_cost if move_cost > _ZERO else last_known_cost
                lots.append([added, additional_cost])
                if additional_cost > _ZERO:
                    last_known_cost = additional_cost
            current_stock = target_quantity

    if not lots:
        return last_known_cost.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)

    simulated_lots: Deque[list[Decimal]] = deque(
        [[qty, cost] for qty, cost in lots])
    remaining = quantity
    accumulated_cost = _ZERO
    baseline_cost = lots[0][1] if lots else last_known_cost

    while simulated_lots and remaining > _ZERO:
        lot_quantity, lot_cost = simulated_lots[0]
        take = min(lot_quantity, remaining)
        accumulated_cost += take * lot_cost
        remaining -= take
        if take >= lot_quantity:
            simulated_lots.popleft()
        else:
            simulated_lots[0][0] = (lot_quantity - take).quantize(_FOUR_PLACES)

    if remaining > _ZERO:
        accumulated_cost += remaining * baseline_cost

    if accumulated_cost <= _ZERO:
        return baseline_cost.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)

    unit_cost = accumulated_cost / quantity
    return unit_cost.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def compute_unit_cost(
    db: Session,
    *,
    product_id: int,
    branch_id: int,
    quantity_out: Decimal | int | float,
    method: str | models.CostingMethod | None = None,
) -> Decimal:
    """Determina el costo unitario de salida según el método configurado."""  # // [PACK30-31-BACKEND]

    required_quantity = _to_decimal(quantity_out)
    if required_quantity <= _ZERO:
        return _ZERO

    costing_method = _resolve_method(method)
    if costing_method == models.CostingMethod.AVG:
        return _current_average_cost(db, product_id).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)

    return _simulate_fifo_cost(
        db,
        product_id=product_id,
        branch_id=branch_id,
        quantity=required_quantity,
    )


def record_stock_move(
    db: Session,
    *,
    product_id: int,
    branch_id: int | None,
    move_type: models.StockMoveType,
    quantity: Decimal | int | float,
    unit_cost: Decimal | None = None,
    reference_id: str | None = None,
    performed_by_id: int | None = None,
) -> models.StockMove:
    """Wrapper para record_move compatible con crud/inventory.py."""
    return record_move(
        db,
        product_id=product_id,
        branch_id=branch_id,
        quantity=quantity,
        move_type=move_type,
        reference=reference_id,
    )
