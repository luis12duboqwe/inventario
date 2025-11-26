"""Servicios para la generación de alertas de inventario."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ..core.settings import (
    InventoryAlertSettings,
    InventoryAlertSeverity,
    inventory_alert_settings,
)
from ..schemas import InventoryAlertDevice, InventoryAlertSummary, LowStockDevice


@dataclass(frozen=True)
class SeverityThresholds:
    """Representa los límites de severidad para un umbral determinado."""

    threshold: int
    warning: int
    critical: int


@dataclass
class InventoryAlertsEvaluation:
    """Resultado completo del cálculo de alertas."""

    items: list[InventoryAlertDevice]
    thresholds: SeverityThresholds
    summary: InventoryAlertSummary


class InventoryAlertsService:
    """Encapsula las reglas para clasificar alertas de inventario."""

    def __init__(self, settings: InventoryAlertSettings | None = None) -> None:
        self._settings = settings or inventory_alert_settings

    @property
    def min_threshold(self) -> int:
        return self._settings.min_low_stock_threshold

    @property
    def max_threshold(self) -> int:
        return self._settings.max_low_stock_threshold

    @property
    def adjustment_variance_threshold(self) -> int:
        return self._settings.adjustment_variance_threshold

    def normalize_threshold(self, value: int | None) -> int:
        """Aplica límites coherentes al umbral recibido."""

        return self._settings.clamp_threshold(value)

    def resolve_thresholds(self, threshold: int) -> SeverityThresholds:
        """Calcula los puntos de advertencia y crítico asociados al umbral."""

        warning_cutoff = self._settings.resolve_warning_cutoff(threshold)
        critical_cutoff = self._settings.resolve_critical_cutoff(
            threshold, warning_cutoff
        )
        return SeverityThresholds(
            threshold=threshold,
            warning=warning_cutoff,
            critical=critical_cutoff,
        )

    def resolve_severity(
        self, quantity: int, thresholds: SeverityThresholds
    ) -> InventoryAlertSeverity:
        """Clasifica una cantidad utilizando los límites calculados."""

        if quantity <= thresholds.critical:
            return "critical"
        if quantity <= thresholds.warning:
            return "warning"
        return "notice"

    def evaluate(
        self,
        devices: Sequence[LowStockDevice],
        *,
        threshold: int | None = None,
    ) -> InventoryAlertsEvaluation:
        """Genera el listado de alertas y su resumen estadístico."""

        normalized_threshold = self.normalize_threshold(threshold)
        severity_thresholds = self.resolve_thresholds(normalized_threshold)
        items: list[InventoryAlertDevice] = []
        summary = InventoryAlertSummary(total=0, critical=0, warning=0, notice=0)

        for device in devices:
            item_data = device.model_dump()
            severity = self.resolve_severity(device.quantity, severity_thresholds)
            item = InventoryAlertDevice.model_validate({
                **item_data,
                "severity": severity,
            })
            items.append(item)
            if severity == "critical":
                summary.critical += 1
            elif severity == "warning":
                summary.warning += 1
            else:
                summary.notice += 1
            summary.total += 1

        return InventoryAlertsEvaluation(
            items=items,
            thresholds=severity_thresholds,
            summary=summary,
        )


alerts_service = InventoryAlertsService()

__all__ = [
    "InventoryAlertsEvaluation",
    "InventoryAlertsService",
    "SeverityThresholds",
    "alerts_service",
]
