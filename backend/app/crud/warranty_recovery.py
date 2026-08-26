"""Compatibilidad temporal para métricas de garantía evolucionadas."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .. import crud_legacy, models, schemas


def get_warranty_metrics(
    db: Session,
    *,
    store_id: int | None = None,
    horizon_days: int = 30,
) -> schemas.WarrantyMetrics:
    """Calcula métricas incluyendo el campo claims_rejected añadido al schema.

    El productor legacy antecede a ese campo. En el modelo persistido no existe
    un estado RECHAZADO; CANCELADO es el cierre equivalente para un reclamo no
    aceptado/resuelto y se reporta como rejected en la API gerencial.
    """
    crud_legacy.refresh_expired_warranties(db)

    statement = (
        select(models.WarrantyAssignment)
        .join(models.WarrantyAssignment.sale_item)
        .join(models.SaleItem.sale)
        .options(joinedload(models.WarrantyAssignment.claims))
    )
    if store_id is not None:
        statement = statement.where(models.Sale.store_id == store_id)

    assignments = list(db.scalars(statement).unique())
    total = len(assignments)
    active = sum(
        1 for assignment in assignments
        if assignment.status == models.WarrantyStatus.ACTIVA
    )
    expired = sum(
        1 for assignment in assignments
        if assignment.status == models.WarrantyStatus.VENCIDA
    )
    expiring_limit = date.today() + timedelta(days=max(horizon_days, 0))
    expiring = sum(
        1
        for assignment in assignments
        if assignment.status == models.WarrantyStatus.ACTIVA
        and assignment.expiration_date <= expiring_limit
    )

    claims_open = 0
    claims_resolved = 0
    claims_rejected = 0
    total_days = 0
    for assignment in assignments:
        total_days += max(
            (assignment.expiration_date - assignment.activation_date).days,
            0,
        )
        for claim in assignment.claims:
            if claim.status in {
                models.WarrantyClaimStatus.ABIERTO,
                models.WarrantyClaimStatus.EN_PROCESO,
            }:
                claims_open += 1
            elif claim.status == models.WarrantyClaimStatus.RESUELTO:
                claims_resolved += 1
            elif claim.status == models.WarrantyClaimStatus.CANCELADO:
                claims_rejected += 1

    average_days = float(total_days / total) if total else 0.0
    return schemas.WarrantyMetrics(
        total_assignments=total,
        active_assignments=active,
        expired_assignments=expired,
        claims_open=claims_open,
        claims_resolved=claims_resolved,
        claims_rejected=claims_rejected,
        expiring_soon=expiring,
        average_coverage_days=round(average_days, 2),
        generated_at=datetime.now(timezone.utc),
    )


__all__ = ["get_warranty_metrics"]
