"""Endpoints dedicados a las alertas de inventario."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from .. import schemas
from ..core.roles import MOVEMENT_ROLES
from ..database import get_db
from ..security import require_roles
from ..services.inventory_alerts import InventoryAlertsService
from ..services.stock_alerts import StockAlertsService

router = APIRouter(prefix="/alerts", tags=["alertas"])

_alerts_service = InventoryAlertsService()
_stock_alerts_service = StockAlertsService(_alerts_service)


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
    service: StockAlertsService = Depends(lambda: _stock_alerts_service),
) -> schemas.InventoryAlertsResponse:
    """Devuelve las alertas de inventario combinando stock y pronósticos."""

    result = service.generate(
        db,
        store_id=store_id,
        threshold=threshold,
        performed_by_id=getattr(current_user, "id", None),
    )
    return schemas.InventoryAlertsResponse(
        settings=result.settings,
        summary=result.summary,
        items=result.items,
    )


__all__ = ["router"]
