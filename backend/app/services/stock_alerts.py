"""Servicios combinados de alertas de inventario con pronóstico."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy.orm import Session

from .. import crud, schemas
from ..crud import log_audit_event
from .inventory_alerts import InventoryAlertsEvaluation, InventoryAlertsService


@dataclass(frozen=True)
class StockAlertResult:
    """Resultado completo con enriquecimiento de pronóstico."""

    settings: schemas.InventoryAlertSettingsResponse
    summary: schemas.InventoryAlertSummary
    items: list[schemas.InventoryAlertDevice]


class StockAlertsService:
    """Orquesta métricas reales y pronósticos para generar alertas accionables."""

    def __init__(self, inventory_service: InventoryAlertsService | None = None) -> None:
        self._inventory_service = inventory_service or InventoryAlertsService()

    def _resolve_store_filter(self, store_id: int | None) -> list[int] | None:
        if store_id is None:
            return None
        if store_id <= 0:
            return None
        return [store_id]

    def _merge_forecast(
        self,
        evaluation: InventoryAlertsEvaluation,
        forecast_rows: Iterable[dict[str, object]],
    ) -> list[schemas.InventoryAlertDevice]:
        forecast_map = {
            int(row.get("device_id")): row for row in forecast_rows if row.get("device_id") is not None
        }
        enriched: list[schemas.InventoryAlertDevice] = []
        for item in evaluation.items:
            base_data = item.model_dump()
            forecast = forecast_map.get(item.device_id)
            insights: list[str] = list(base_data.get("insights", []))
            extra_payload: dict[str, object] = {}
            if forecast:
                projected_days = forecast.get("projected_days")
                if isinstance(projected_days, (int, float)):
                    extra_payload["projected_days"] = int(projected_days)
                else:
                    extra_payload["projected_days"] = None
                avg_daily = forecast.get("average_daily_sales")
                extra_payload["average_daily_sales"] = (
                    float(avg_daily) if isinstance(avg_daily, (int, float)) else None
                )
                trend = forecast.get("trend")
                if isinstance(trend, str):
                    extra_payload["trend"] = trend
                confidence = forecast.get("confidence")
                if isinstance(confidence, (int, float)):
                    extra_payload["confidence"] = float(confidence)
                sold_units = forecast.get("sold_units")
                if isinstance(sold_units, (int, float)) and sold_units > 0:
                    insights.append(f"{int(sold_units)} uds vendidas en ventana histórica")
                projected = extra_payload.get("projected_days")
                if isinstance(projected, int):
                    if projected <= 3:
                        insights.append("Agotamiento estimado ≤3 días")
                    elif projected <= 7:
                        insights.append("Agotamiento estimado ≤7 días")
            minimum_stock = base_data.get("minimum_stock", 0)
            reorder_point = base_data.get("reorder_point", 0)
            quantity = base_data.get("quantity", 0)
            if isinstance(quantity, (int, float)):
                quantity_int = int(quantity)
            else:
                quantity_int = 0
            if isinstance(minimum_stock, (int, float)) and quantity_int <= int(minimum_stock):
                insights.append("Por debajo del stock mínimo")
            if isinstance(reorder_point, (int, float)) and quantity_int <= int(reorder_point):
                insights.append("Punto de reorden alcanzado")
            extra_payload["insights"] = insights
            enriched.append(
                schemas.InventoryAlertDevice.model_validate({
                    **base_data,
                    **extra_payload,
                })
            )
        return enriched

    def generate(
        self,
        db: Session,
        *,
        store_id: int | None = None,
        threshold: int | None = None,
        performed_by_id: int | None = None,
    ) -> StockAlertResult:
        normalized_threshold = self._inventory_service.normalize_threshold(threshold)
        metrics = crud.compute_inventory_metrics(
            db, low_stock_threshold=normalized_threshold
        )
        raw_devices = metrics.get("low_stock_devices", [])
        devices = [
            schemas.LowStockDevice.model_validate(entry)
            for entry in raw_devices
            if store_id is None or entry.get("store_id") == store_id
        ]
        evaluation = self._inventory_service.evaluate(
            devices, threshold=normalized_threshold
        )
        forecast_rows = crud.calculate_stockout_forecast(
            db,
            store_ids=self._resolve_store_filter(store_id),
            limit=None,
        )
        enriched_items = self._merge_forecast(evaluation, forecast_rows)
        settings = schemas.InventoryAlertSettingsResponse(
            threshold=evaluation.thresholds.threshold,
            minimum_threshold=self._inventory_service.min_threshold,
            maximum_threshold=self._inventory_service.max_threshold,
            warning_cutoff=evaluation.thresholds.warning,
            critical_cutoff=evaluation.thresholds.critical,
            adjustment_variance_threshold=self._inventory_service.adjustment_variance_threshold,
        )
        log_audit_event(
            db,
            action="inventory_stock_alerts_evaluated",
            entity_type="inventory_alert",
            entity_id=store_id or "global",
            performed_by_id=performed_by_id,
            details={
                "store_id": store_id,
                "threshold": settings.threshold,
                "summary": evaluation.summary.model_dump(),
                "critical_devices": [item.device_id for item in enriched_items if item.severity == "critical"],
            },
        )
        return StockAlertResult(
            settings=settings,
            summary=evaluation.summary,
            items=enriched_items,
        )


__all__ = ["StockAlertResult", "StockAlertsService"]
