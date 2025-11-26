from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from .. import crud, schemas
from ..crud import log_audit_event


@dataclass(frozen=True)
class MinimumStockResult:
    summary: schemas.MinimumStockSummary
    items: list[schemas.MinimumStockAlert]


class MinimumStockService:
    """Detecta dispositivos por debajo del mínimo y del punto de reorden."""

    def detect(
        self,
        db: Session,
        *,
        store_id: int | None = None,
        performed_by_id: int | None = None,
    ) -> MinimumStockResult:
        raw_items = crud.list_devices_below_minimum_thresholds(db, store_id=store_id)

        alerts: list[schemas.MinimumStockAlert] = []
        below_minimum = 0
        below_reorder = 0

        for row in raw_items:
            minimum_stock = int(row.get("minimum_stock", 0) or 0)
            reorder_point = int(row.get("reorder_point", 0) or 0)
            quantity = int(row.get("quantity", 0) or 0)

            is_below_minimum = minimum_stock > 0 and quantity <= minimum_stock
            is_below_reorder = reorder_point > 0 and quantity <= reorder_point

            below_minimum += 1 if is_below_minimum else 0
            below_reorder += 1 if is_below_reorder else 0

            alerts.append(
                schemas.MinimumStockAlert.model_validate(
                    {
                        **row,
                        "below_minimum": is_below_minimum,
                        "below_reorder_point": is_below_reorder,
                    }
                )
            )

        summary = schemas.MinimumStockSummary(
            total=len(alerts),
            below_minimum=below_minimum,
            below_reorder_point=below_reorder,
        )

        log_audit_event(
            db,
            action="inventory_minimum_stock_evaluated",
            entity_type="inventory_alert",
            entity_id=store_id or "global",
            performed_by_id=performed_by_id,
            details={
                "store_id": store_id,
                "total_items": summary.total,
                "below_minimum": summary.below_minimum,
                "below_reorder_point": summary.below_reorder_point,
            },
        )

        return MinimumStockResult(summary=summary, items=alerts)


__all__ = ["MinimumStockResult", "MinimumStockService"]
