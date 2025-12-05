from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict, field_serializer, field_validator, computed_field

from .common import DashboardChartPoint
from .inventory_reports import InventoryTotals, StoreValueMetric, LowStockDevice
from .audit import DashboardAuditAlerts, AuditHighlight, AuditAcknowledgedEntity
from .sync import SyncOutboxStatsEntry, SyncHybridProgressSummary
from .system_logs import SystemLogEntry, SystemErrorEntry, SystemLogLevel


class GlobalReportFiltersState(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None
    module: str | None = None
    severity: SystemLogLevel | None = None

    @field_serializer("date_from", "date_to", when_used="json")
    @classmethod
    def _serialize_datetime(cls, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class GlobalReportTotals(BaseModel):
    logs: int = Field(default=0, ge=0)
    errors: int = Field(default=0, ge=0)
    info: int = Field(default=0, ge=0)
    warning: int = Field(default=0, ge=0)
    error: int = Field(default=0, ge=0)
    critical: int = Field(default=0, ge=0)
    sync_pending: int = Field(default=0, ge=0)
    sync_failed: int = Field(default=0, ge=0)
    last_activity_at: datetime | None = None

    @field_serializer("last_activity_at", when_used="json")
    @classmethod
    def _serialize_last_activity(cls, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class GlobalReportBreakdownItem(BaseModel):
    name: str
    total: int = Field(default=0, ge=0)


class GlobalReportAlert(BaseModel):
    type: Literal["critical_log", "system_error", "sync_failure"]
    level: SystemLogLevel
    message: str
    module: str | None = None
    occurred_at: datetime | None = None
    reference: str | None = None
    count: int = Field(default=1, ge=1)

    @field_serializer("occurred_at", when_used="json")
    @classmethod
    def _serialize_occurred_at(cls, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class GlobalReportOverview(BaseModel):
    generated_at: datetime
    filters: GlobalReportFiltersState
    totals: GlobalReportTotals
    module_breakdown: list[GlobalReportBreakdownItem]
    severity_breakdown: list[GlobalReportBreakdownItem]
    recent_logs: list[SystemLogEntry]
    recent_errors: list[SystemErrorEntry]
    alerts: list[GlobalReportAlert]

    @field_serializer("generated_at", when_used="json")
    @classmethod
    def _serialize_generated_at(cls, value: datetime) -> str:
        return value.isoformat()


class GlobalReportSeriesPoint(BaseModel):
    date: date
    info: int = Field(default=0, ge=0)
    warning: int = Field(default=0, ge=0)
    error: int = Field(default=0, ge=0)
    critical: int = Field(default=0, ge=0)
    system_errors: int = Field(default=0, ge=0)


class ObservabilityLatencySample(BaseModel):
    entity_type: str
    pending: int
    failed: int
    oldest_pending_seconds: float | None
    latest_update: datetime | None

    @field_serializer("latest_update", when_used="json")
    @classmethod
    def _serialize_latest_update(cls, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class ObservabilityLatencySummary(BaseModel):
    average_seconds: float | None
    percentile_95_seconds: float | None
    max_seconds: float | None
    samples: list[ObservabilityLatencySample]


class ObservabilityErrorSummary(BaseModel):
    total_logs: int
    total_errors: int
    info: int
    warning: int
    error: int
    critical: int
    latest_error_at: datetime | None

    @field_serializer("latest_error_at", when_used="json")
    @classmethod
    def _serialize_latest_error_at(cls, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class ObservabilitySyncSummary(BaseModel):
    outbox_stats: list[SyncOutboxStatsEntry]
    total_pending: int
    total_failed: int
    hybrid_progress: SyncHybridProgressSummary | None


class ObservabilityNotification(BaseModel):
    id: str
    title: str
    message: str
    severity: SystemLogLevel
    occurred_at: datetime | None = None
    reference: str | None = None

    @field_serializer("occurred_at", when_used="json")
    @classmethod
    def _serialize_occurred_at(cls, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class ObservabilitySnapshot(BaseModel):
    generated_at: datetime
    latency: ObservabilityLatencySummary
    errors: ObservabilityErrorSummary
    sync: ObservabilitySyncSummary
    logs: list[SystemLogEntry]
    system_errors: list[SystemErrorEntry]
    alerts: list[GlobalReportAlert]
    notifications: list[ObservabilityNotification]

    @field_serializer("generated_at", when_used="json")
    @classmethod
    def _serialize_generated_at(cls, value: datetime) -> str:
        return value.isoformat()


class GlobalReportDashboard(BaseModel):
    generated_at: datetime
    filters: GlobalReportFiltersState
    activity_series: list[GlobalReportSeriesPoint]
    module_distribution: list[GlobalReportBreakdownItem]
    severity_distribution: list[GlobalReportBreakdownItem]

    @field_serializer("generated_at", when_used="json")
    @classmethod
    def _serialize_generated_at(cls, value: datetime) -> str:
        return value.isoformat()


# // [PACK29-*] DTOs de reportes de ventas (resumen, productos y cierre de caja)
class SalesSummaryReport(BaseModel):
    total_sales: float = Field(default=0.0, alias="totalSales")
    total_orders: int = Field(default=0, alias="totalOrders")
    avg_ticket: float = Field(default=0.0, alias="avgTicket")
    returns_count: int = Field(default=0, alias="returnsCount")
    net: float = Field(default=0.0, alias="net")

    model_config = ConfigDict(populate_by_name=True)


# // [PACK29-*] DTO para filas del top de productos vendidos
class SalesByProductItem(BaseModel):
    sku: str
    name: str
    quantity: int = Field(default=0, alias="qty", ge=0)
    gross: float = Field(default=0.0)
    net: float = Field(default=0.0)

    model_config = ConfigDict(populate_by_name=True)


# // [PACK29-*] DTO de sugerencia de cierre de caja diario
class CashCloseReport(BaseModel):
    opening: float = Field(default=0.0)
    sales_gross: float = Field(default=0.0, alias="salesGross")
    refunds: float = Field(default=0.0)
    incomes: float = Field(default=0.0)
    expenses: float = Field(default=0.0)
    closing_suggested: float = Field(default=0.0, alias="closingSuggested")

    model_config = ConfigDict(populate_by_name=True)


class AuditReminderEntry(BaseModel):
    entity_type: str
    entity_id: str
    first_seen: datetime
    last_seen: datetime
    occurrences: int = Field(..., ge=1)
    latest_action: str
    latest_details: str | None = None
    status: Literal["pending", "acknowledged"] = Field(default="pending")
    acknowledged_at: datetime | None = None
    acknowledged_by_id: int | None = None
    acknowledged_by_name: str | None = None
    acknowledged_note: str | None = None

    @field_serializer("first_seen", "last_seen", when_used="json")
    @classmethod
    def _serialize_timestamp(cls, value: datetime) -> str:
        return value.isoformat()

    @field_serializer("acknowledged_at")
    @classmethod
    def _serialize_ack(cls, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class AuditReminderSummary(BaseModel):
    threshold_minutes: int = Field(..., ge=0)
    min_occurrences: int = Field(..., ge=1)
    total: int = Field(..., ge=0)
    pending_count: int = Field(..., ge=0)
    acknowledged_count: int = Field(..., ge=0)
    persistent: list[AuditReminderEntry]


class AuditAcknowledgementCreate(BaseModel):
    entity_type: str = Field(..., min_length=1, max_length=80)
    entity_id: str = Field(..., min_length=1, max_length=80)
    note: str | None = Field(default=None, max_length=255)

    @field_validator("entity_type", "entity_id")
    @classmethod
    def _normalize_identifier(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Valor requerido")
        return normalized

    @field_validator("note")
    @classmethod
    def _normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AuditAcknowledgementResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    acknowledged_at: datetime
    acknowledged_by_id: int | None = None
    acknowledged_by_name: str | None = None
    note: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("acknowledged_at")
    @classmethod
    def _serialize_acknowledged_at(cls, value: datetime) -> str:
        return value.isoformat()


class DashboardGlobalMetrics(BaseModel):
    total_sales: float
    sales_count: int
    total_stock: int
    open_repairs: int
    gross_profit: float


class DashboardSalesEntityMetric(BaseModel):
    label: str
    value: float
    quantity: int | None = None
    percentage: float | None = None


class DashboardSalesInsights(BaseModel):
    average_ticket: float
    top_products: list[DashboardSalesEntityMetric] = Field(
        default_factory=list)
    top_customers: list[DashboardSalesEntityMetric] = Field(
        default_factory=list)
    payment_mix: list[DashboardSalesEntityMetric] = Field(default_factory=list)


class DashboardReceivableCustomer(BaseModel):
    customer_id: int
    name: str
    outstanding_debt: float
    available_credit: float | None = None


class DashboardReceivableMetrics(BaseModel):
    total_outstanding_debt: float
    customers_with_debt: int
    moroso_flagged: int
    top_debtors: list[DashboardReceivableCustomer] = Field(
        default_factory=list)


class InventoryMetricsResponse(BaseModel):
    totals: InventoryTotals
    top_stores: list[StoreValueMetric]
    low_stock_devices: list[LowStockDevice]
    global_performance: DashboardGlobalMetrics
    sales_insights: DashboardSalesInsights
    accounts_receivable: DashboardReceivableMetrics
    sales_trend: list[DashboardChartPoint] = Field(default_factory=list)
    stock_breakdown: list[DashboardChartPoint] = Field(default_factory=list)
    repair_mix: list[DashboardChartPoint] = Field(default_factory=list)
    profit_breakdown: list[DashboardChartPoint] = Field(default_factory=list)
    audit_alerts: DashboardAuditAlerts
