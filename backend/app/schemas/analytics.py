from __future__ import annotations
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RotationMetric(BaseModel):
    store_id: int
    store_name: str
    device_id: int
    sku: str
    name: str
    sold_units: int
    received_units: int
    rotation_rate: float


class AnalyticsRotationResponse(BaseModel):
    items: list[RotationMetric]


class ReportFilterState(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None
    store_ids: list[int] = Field(default_factory=lambda: [])
    category: str | None = None


class SalesByStoreMetric(BaseModel):
    store_id: int
    store_name: str
    revenue: float
    orders: int
    units: int


class SalesByCategoryMetric(BaseModel):
    category: str
    revenue: float
    orders: int
    units: int


class SalesTimeseriesPoint(BaseModel):
    date: date
    revenue: float
    orders: int
    units: int


class ProfitMarginMetric(BaseModel):
    store_id: int
    store_name: str
    revenue: float
    cost: float
    profit: float
    margin_percent: float


class FinancialTotals(BaseModel):
    revenue: float
    cost: float
    profit: float
    margin_percent: float


class FinancialPerformanceReport(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    generated_at: datetime
    filters: ReportFilterState
    rotation: list[RotationMetric]
    profit_by_store: list[ProfitMarginMetric]
    sales_by_store: list[SalesByStoreMetric]
    sales_by_category: list[SalesByCategoryMetric]
    sales_trend: list[SalesTimeseriesPoint]
    totals: FinancialTotals


class InventoryPerformanceReport(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    generated_at: datetime
    filters: ReportFilterState
    rotation: list[RotationMetric]
    profit_by_store: list[ProfitMarginMetric]
    sales_by_store: list[SalesByStoreMetric]
    sales_by_category: list[SalesByCategoryMetric]
    sales_trend: list[SalesTimeseriesPoint]


class AgingMetric(BaseModel):
    device_id: int
    sku: str
    name: str
    store_id: int
    store_name: str
    days_in_stock: int
    quantity: int


class AnalyticsAgingResponse(BaseModel):
    items: list[AgingMetric]


class StockoutForecastMetric(BaseModel):
    device_id: int
    sku: str
    name: str
    store_id: int
    store_name: str
    average_daily_sales: float
    projected_days: int | None
    quantity: int
    trend: str
    trend_score: float
    confidence: float
    alert_level: str | None
    sold_units: int


class AnalyticsForecastResponse(BaseModel):
    items: list[StockoutForecastMetric]


class StoreComparativeMetric(BaseModel):
    store_id: int
    store_name: str
    device_count: int
    total_units: int
    inventory_value: float
    average_rotation: float
    average_aging_days: float
    sales_last_30_days: float
    sales_count_last_30_days: int


class AnalyticsComparativeResponse(BaseModel):
    items: list[StoreComparativeMetric]


class AnalyticsProfitMarginResponse(BaseModel):
    items: list[ProfitMarginMetric]


class SalesProjectionMetric(BaseModel):
    store_id: int
    store_name: str
    average_daily_units: float
    average_ticket: float
    projected_units: float
    projected_revenue: float
    confidence: float
    trend: str
    trend_score: float
    revenue_trend_score: float
    r2_revenue: float


class AnalyticsSalesProjectionResponse(BaseModel):
    items: list[SalesProjectionMetric]


class StoreSalesForecast(BaseModel):
    store_id: int
    store_name: str
    average_daily_units: float
    projected_units: float
    projected_revenue: float
    trend: str
    confidence: float


class StoreSalesForecastResponse(BaseModel):
    items: list[StoreSalesForecast]


class ReorderSuggestion(BaseModel):
    store_id: int
    store_name: str
    device_id: int
    sku: str
    name: str
    quantity: int
    reorder_point: int
    minimum_stock: int
    recommended_order: int
    projected_days: int | None = None
    average_daily_sales: float | None = None
    reason: str


class ReorderSuggestionsResponse(BaseModel):
    items: list[ReorderSuggestion]


class ReturnAnomaly(BaseModel):
    user_id: int
    user_name: str | None
    return_count: int
    total_units: int
    last_return: datetime | None = None
    store_count: int
    z_score: float
    threshold: float
    is_anomalous: bool = False


class ReturnAnomaliesResponse(BaseModel):
    items: list[ReturnAnomaly]


class AnalyticsAlert(BaseModel):
    type: str
    level: str
    message: str
    store_id: int | None
    store_name: str
    device_id: int | None
    sku: str | None


class AnalyticsAlertsResponse(BaseModel):
    items: list[AnalyticsAlert]


class RiskMetric(BaseModel):
    total: int
    average: float
    maximum: float
    last_seen: datetime | None = None


class RiskAlert(BaseModel):
    code: str
    title: str
    description: str
    severity: Literal["info", "media", "alta", "critica"]
    occurrences: int
    detail: dict[str, object] | None = None


class RiskAlertsResponse(BaseModel):
    generated_at: datetime
    alerts: list[RiskAlert]
    metrics: dict[str, RiskMetric]


class StoreRealtimeWidget(BaseModel):
    store_id: int
    store_name: str
    inventory_value: float
    sales_today: float
    last_sale_at: datetime | None
    low_stock_devices: int
    pending_repairs: int
    last_sync_at: datetime | None
    trend: str
    trend_score: float
    confidence: float


class AnalyticsRealtimeResponse(BaseModel):
    items: list[StoreRealtimeWidget]


class AnalyticsCategoriesResponse(BaseModel):
    categories: list[str]


class PurchaseSupplierMetric(BaseModel):
    store_id: int
    store_name: str
    supplier: str
    device_count: int
    total_ordered: int
    total_received: int
    pending_backorders: int
    total_cost: float
    average_unit_cost: float
    average_rotation: float
    average_days_in_stock: float
    last_purchase_at: datetime | None


class PurchaseAnalyticsResponse(BaseModel):
    items: list[PurchaseSupplierMetric]
