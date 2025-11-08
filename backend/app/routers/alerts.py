"""Endpoints dedicados a las alertas de inventario."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..core.roles import MOVEMENT_ROLES
from ..database import get_db
from ..security import require_roles
from ..services.inventory_alerts import InventoryAlertsService

router = APIRouter(prefix="/alerts", tags=["alertas"])

_alerts_service = InventoryAlertsService()


@router.get(
    "/inventory",
    response_model=schemas.InventoryAlertsResponse,
    status_code=status.HTTP_200_OK,
)
def list_inventory_alerts(
    store_id: int | None = Query(default=None, ge=1),
    threshold: int | None = Query(
        default=None,
        description=(
            "Umbral personalizado para calcular alertas;"
            " se ajusta automáticamente al rango permitido."
        ),
    ),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(MOVEMENT_ROLES)),
    service: InventoryAlertsService = Depends(lambda: _alerts_service),
) -> schemas.InventoryAlertsResponse:
    """Devuelve las alertas de inventario considerando el umbral solicitado."""

    normalized_threshold = service.normalize_threshold(threshold)
    metrics = crud.compute_inventory_metrics(
        db, low_stock_threshold=normalized_threshold
    )
    raw_devices = metrics.get("low_stock_devices", [])
    devices = [
        schemas.LowStockDevice.model_validate(entry)
        for entry in raw_devices
        if store_id is None or entry["store_id"] == store_id
    ]

    evaluation = service.evaluate(devices, threshold=normalized_threshold)
    return schemas.InventoryAlertsResponse(
        settings=schemas.InventoryAlertSettingsResponse(
            threshold=evaluation.thresholds.threshold,
            minimum_threshold=service.min_threshold,
            maximum_threshold=service.max_threshold,
            warning_cutoff=evaluation.thresholds.warning,
            critical_cutoff=evaluation.thresholds.critical,
            adjustment_variance_threshold=service.adjustment_variance_threshold,
        ),
        summary=evaluation.summary,
        items=evaluation.items,
    )


__all__ = ["router"]
