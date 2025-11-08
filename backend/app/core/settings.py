"""Configuración dedicada a las alertas de inventario."""
from __future__ import annotations

from functools import lru_cache
from math import ceil
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

InventoryAlertSeverity = Literal["critical", "warning", "notice"]


class InventoryAlertSettings(BaseSettings):
    """Valores de configuración para calcular alertas de inventario."""

    model_config = SettingsConfigDict(
        env_prefix="softmobile_",
        case_sensitive=False,
        extra="allow",
    )

    default_low_stock_threshold: int = Field(
        default=5,
        ge=0,
        le=500,
        validation_alias=AliasChoices(
            "INVENTORY_LOW_STOCK_THRESHOLD",
            "SOFTMOBILE_LOW_STOCK_THRESHOLD",
        ),
        description="Umbral predeterminado de stock bajo por sucursal.",
    )
    min_low_stock_threshold: int = Field(
        default=0,
        ge=0,
        le=500,
        description="Valor mínimo permitido para el umbral configurable.",
    )
    max_low_stock_threshold: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Valor máximo permitido para el umbral configurable.",
    )
    warning_ratio: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Porcentaje del umbral considerado como advertencia.",
    )
    critical_ratio: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Porcentaje del umbral considerado crítico.",
    )
    minimum_warning_units: int = Field(
        default=3,
        ge=0,
        le=500,
        description="Cantidad mínima para clasificar como advertencia, aun con ratios bajos.",
    )
    minimum_critical_units: int = Field(
        default=1,
        ge=0,
        le=500,
        description="Cantidad mínima para clasificar como crítico, aun con ratios bajos.",
    )
    adjustment_variance_threshold: int = Field(
        default=3,
        ge=0,
        le=500,
        validation_alias=AliasChoices(
            "INVENTORY_ADJUSTMENT_VARIANCE_THRESHOLD",
            "SOFTMOBILE_ADJUSTMENT_VARIANCE_THRESHOLD",
        ),
        description="Variación mínima para registrar alertas por ajustes manuales.",
    )

    def clamp_threshold(self, value: int | None) -> int:
        """Restringe el umbral recibido a los límites permitidos."""

        if value is None:
            value = self.default_low_stock_threshold
        if value < self.min_low_stock_threshold:
            return self.min_low_stock_threshold
        if value > self.max_low_stock_threshold:
            return self.max_low_stock_threshold
        return value

    def resolve_warning_cutoff(self, threshold: int) -> int:
        """Calcula el punto de advertencia con base en el umbral actual."""

        if threshold <= 0:
            return 0
        computed = ceil(threshold * self.warning_ratio)
        return min(
            threshold,
            max(self.minimum_warning_units, computed),
        )

    def resolve_critical_cutoff(self, threshold: int, warning_cutoff: int | None = None) -> int:
        """Calcula el punto crítico respetando el límite de advertencia."""

        if threshold <= 0:
            return 0
        computed = ceil(threshold * self.critical_ratio)
        warning_limit = warning_cutoff if warning_cutoff is not None else self.resolve_warning_cutoff(threshold)
        return min(
            warning_limit,
            max(self.minimum_critical_units, computed),
        )

    def resolve_severity(self, quantity: int, threshold: int) -> InventoryAlertSeverity:
        """Clasifica la severidad de un dispositivo según su cantidad actual."""

        warning_cutoff = self.resolve_warning_cutoff(threshold)
        critical_cutoff = self.resolve_critical_cutoff(threshold, warning_cutoff)

        if quantity <= critical_cutoff:
            return "critical"
        if quantity <= warning_cutoff:
            return "warning"
        return "notice"


@lru_cache()
def get_inventory_alert_settings() -> InventoryAlertSettings:
    """Devuelve la configuración cacheada para las alertas de inventario."""

    return InventoryAlertSettings()


inventory_alert_settings = get_inventory_alert_settings()

__all__ = [
    "InventoryAlertSettings",
    "InventoryAlertSeverity",
    "get_inventory_alert_settings",
    "inventory_alert_settings",
]
