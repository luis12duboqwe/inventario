"""Compatibilidad acotada para contratos perdidos durante la migración CRUD.

Las funciones de este módulo deben desaparecer cuando REC-0004/R3 incorpore cada
comportamiento directamente en su módulo canónico. Se mantienen separadas para
no volver a editar el archivo legacy recuperado.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from .. import models, schemas
from ..services.inventory_availability import invalidate_inventory_availability_cache
from .inventory import create_inventory_movement as _create_inventory_movement


def create_inventory_movement(
    db: Session,
    store_id: int,
    payload: schemas.MovementCreate,
    *,
    performed_by_id: int | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
) -> models.InventoryMovement:
    """Crea el movimiento e invalida la vista agregada de disponibilidad.

    El CRUD especializado actual modifica correctamente ``Device.quantity`` pero
    la extracción perdió la invalidación del cache de disponibilidad, dejando
    respuestas antiguas hasta vencer el TTL.
    """

    movement = _create_inventory_movement(
        db,
        store_id,
        payload,
        performed_by_id=performed_by_id,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    invalidate_inventory_availability_cache()
    return movement


__all__ = ["create_inventory_movement"]
