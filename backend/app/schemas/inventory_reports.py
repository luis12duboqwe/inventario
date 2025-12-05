from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    field_serializer,
    computed_field,
    AliasChoices,
    field_validator,
)

from ..models import MovementType
from .audit import AuditTrailInfo


class InventoryTotals(BaseModel):
    stores: int
    devices: int
    total_units: int
    total_value: Decimal

    @field_serializer("total_value")
    @classmethod
    def _serialize_totals_value(cls, value: Decimal) -> float:
        return float(value)


class InventoryValuation(BaseModel):
    store_id: int
    store_name: str
    device_id: int
    sku: str
    device_name: str
    categoria: str
    quantity: int
    costo_promedio_ponderado: Decimal
    valor_total_producto: Decimal
    valor_costo_producto: Decimal
    valor_total_tienda: Decimal
    valor_total_general: Decimal
    valor_costo_tienda: Decimal
    valor_costo_general: Decimal
    margen_unitario: Decimal
    margen_producto_porcentaje: Decimal
    valor_total_categoria: Decimal
    margen_categoria_valor: Decimal
    margen_categoria_porcentaje: Decimal
    margen_total_tienda: Decimal
    margen_total_general: Decimal
    ventas_totales: int
    ventas_30_dias: int
    ventas_90_dias: int
    ultima_venta: datetime | None
    ultima_compra: datetime | None
    ultimo_movimiento: datetime | None
    rotacion_30_dias: Decimal
    rotacion_90_dias: Decimal
    rotacion_total: Decimal
    dias_sin_movimiento: int | None

    @field_serializer(
        "costo_promedio_ponderado",
        "valor_total_producto",
        "valor_costo_producto",
        "valor_total_tienda",
        "valor_total_general",
        "valor_costo_tienda",
        "valor_costo_general",
        "margen_unitario",
        "valor_total_categoria",
        "margen_categoria_valor",
        "margen_total_tienda",
        "margen_total_general",
        "rotacion_30_dias",
        "rotacion_90_dias",
        "rotacion_total",
    )
    @classmethod
    def _serialize_decimal(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("margen_producto_porcentaje", "margen_categoria_porcentaje")
    @classmethod
    def _serialize_percentage(cls, value: Decimal) -> float:
        return float(value)


class MovementPeriodSummary(BaseModel):
    periodo: str
    total_movimientos: int
    total_unidades: int
    total_valor: Decimal

    @field_serializer("total_valor")
    @classmethod
    def _serialize_total_value(cls, value: Decimal) -> float:
        return float(value)


class MovementTypeSummary(BaseModel):
    tipo_movimiento: MovementType
    total_movimientos: int
    total_unidades: int
    total_valor: Decimal

    @field_serializer("total_valor")
    @classmethod
    def _serialize_total_value(cls, value: Decimal) -> float:
        return float(value)


class MovementReportEntry(BaseModel):
    id: int
    tipo_movimiento: MovementType
    cantidad: int
    valor_total: Decimal
    sucursal_destino_id: int | None
    sucursal_destino: str | None
    sucursal_origen_id: int | None
    sucursal_origen: str | None
    comentario: str | None
    usuario: str | None
    referencia_tipo: str | None = None
    referencia_id: str | None = None
    fecha: datetime
    ultima_accion: AuditTrailInfo | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("valor_total")
    @classmethod
    def _serialize_total_value(cls, value: Decimal) -> float:
        return float(value)

    @computed_field(return_type=str | None, alias="referencia")
    def referencia_compuesta(self) -> str | None:
        if self.referencia_tipo and self.referencia_id:
            return f"{self.referencia_tipo}:{self.referencia_id}"
        return None


class InventoryMovementsSummary(BaseModel):
    total_movimientos: int
    total_unidades: int
    total_valor: Decimal
    por_tipo: list[MovementTypeSummary]

    @field_serializer("total_valor")
    @classmethod
    def _serialize_total_value(cls, value: Decimal) -> float:
        return float(value)


class InventoryMovementsReport(BaseModel):
    resumen: InventoryMovementsSummary
    periodos: list[MovementPeriodSummary]
    movimientos: list[MovementReportEntry]


class TopProductReportItem(BaseModel):
    device_id: int
    sku: str
    nombre: str
    store_id: int
    store_name: str
    unidades_vendidas: int
    ingresos_totales: Decimal
    margen_estimado: Decimal

    @field_serializer("ingresos_totales", "margen_estimado")
    @classmethod
    def _serialize_top_values(cls, value: Decimal) -> float:
        return float(value)


class TopProductsReport(BaseModel):
    items: list[TopProductReportItem]
    total_unidades: int
    total_ingresos: Decimal

    @field_serializer("total_ingresos")
    @classmethod
    def _serialize_total_income(cls, value: Decimal) -> float:
        return float(value)


class InventoryValueStore(BaseModel):
    store_id: int
    store_name: str
    valor_total: Decimal
    valor_costo: Decimal
    margen_total: Decimal

    @field_serializer("valor_total", "valor_costo", "margen_total")
    @classmethod
    def _serialize_value_fields(cls, value: Decimal) -> float:
        return float(value)


class InventoryValueTotals(BaseModel):
    valor_total: Decimal
    valor_costo: Decimal
    margen_total: Decimal

    @field_serializer("valor_total", "valor_costo", "margen_total")
    @classmethod
    def _serialize_totals(cls, value: Decimal) -> float:
        return float(value)


class InventoryValueReport(BaseModel):
    stores: list[InventoryValueStore]
    totals: InventoryValueTotals


class InactiveProductEntry(BaseModel):
    store_id: int
    store_name: str
    device_id: int
    sku: str
    device_name: str
    categoria: str
    quantity: int
    valor_total_producto: Decimal
    ultima_venta: datetime | None
    ultima_compra: datetime | None
    ultimo_movimiento: datetime | None
    dias_sin_movimiento: int | None
    ventas_30_dias: int
    ventas_90_dias: int
    rotacion_30_dias: Decimal
    rotacion_90_dias: Decimal
    rotacion_total: Decimal

    @field_serializer(
        "valor_total_producto",
        "rotacion_30_dias",
        "rotacion_90_dias",
        "rotacion_total",
    )
    @classmethod
    def _serialize_inactive_decimal(cls, value: Decimal) -> float:
        return float(value)


class InactiveProductReportFilters(BaseModel):
    store_ids: list[int] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    min_days_without_movement: int = 30


class InactiveProductReportTotals(BaseModel):
    total_products: int
    total_units: int
    total_value: Decimal
    average_days_without_movement: float | None
    max_days_without_movement: int | None

    @field_serializer("total_value")
    @classmethod
    def _serialize_inactive_total(cls, value: Decimal) -> float:
        return float(value)


class InactiveProductReport(BaseModel):
    generated_at: datetime
    filters: InactiveProductReportFilters
    totals: InactiveProductReportTotals
    items: list[InactiveProductEntry]


class InventoryCurrentStore(BaseModel):
    store_id: int
    store_name: str
    device_count: int
    total_units: int
    total_value: Decimal

    @field_serializer("total_value")
    @classmethod
    def _serialize_current_value(cls, value: Decimal) -> float:
        return float(value)


class InventoryCurrentReport(BaseModel):
    stores: list[InventoryCurrentStore]
    totals: InventoryTotals


class InventoryIntegrityDeviceStatus(BaseModel):
    store_id: int
    store_name: str | None
    device_id: int
    sku: str | None
    quantity_actual: int
    quantity_calculada: int
    costo_actual: Decimal
    costo_calculado: Decimal
    last_movement_id: int | None
    last_movement_fecha: datetime | None
    issues: list[str] = Field(default_factory=list)

    @field_serializer("costo_actual")
    @classmethod
    def _serialize_costo_actual(cls, value: Decimal) -> float:
        return float(value)

    @field_serializer("costo_calculado")
    @classmethod
    def _serialize_costo_calculado(cls, value: Decimal) -> float:
        return float(value)


class InventoryIntegritySummary(BaseModel):
    dispositivos_evaluados: int
    dispositivos_inconsistentes: int
    discrepancias_totales: int


class InventoryIntegrityReport(BaseModel):
    resumen: InventoryIntegritySummary
    dispositivos: list[InventoryIntegrityDeviceStatus]


class StoreValueMetric(BaseModel):
    store_id: int
    store_name: str
    device_count: int
    total_units: int
    total_value: Decimal

    @field_serializer("total_value")
    @classmethod
    def _serialize_metric_value(cls, value: Decimal) -> float:
        return float(value)


class LowStockDevice(BaseModel):
    store_id: int
    store_name: str
    device_id: int
    sku: str
    name: str
    quantity: int
    unit_price: Decimal


class InventoryAlertDevice(LowStockDevice):
    severity: Literal["critical", "warning", "notice"]
    projected_days: int | None = None
    average_daily_sales: float | None = None
    trend: str | None = None
    confidence: float | None = None
    insights: list[str] = Field(default_factory=list)


class InventoryAlertSummary(BaseModel):
    total: int
    critical: int
    warning: int
    notice: int


class InventoryAlertSettingsResponse(BaseModel):
    threshold: int
    minimum_threshold: int
    maximum_threshold: int
    warning_cutoff: int
    critical_cutoff: int
    adjustment_variance_threshold: int


class InventoryAlertsResponse(BaseModel):
    settings: InventoryAlertSettingsResponse
    summary: InventoryAlertSummary
    items: list[InventoryAlertDevice]


class MinimumStockAlert(LowStockDevice):
    below_minimum: bool = False
    below_reorder_point: bool = False


class MinimumStockSummary(BaseModel):
    total: int
    below_minimum: int
    below_reorder_point: int


class MinimumStockAlertsResponse(BaseModel):
    summary: MinimumStockSummary
    items: list[MinimumStockAlert]
