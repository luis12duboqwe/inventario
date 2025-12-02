import { API_URL, request } from "./client";

export type RotationMetric = {
  device_id: number;
  sku: string;
  name: string;
  store_id: number;
  store_name: string;
  average_days_in_stock: number;
  turnover_rate: number;
  sold_units: number;
  current_stock: number;
  last_sale_at: string | null;
};

export type AnalyticsRotation = {
  items: RotationMetric[];
};

export type AgingMetric = {
  device_id: number;
  sku: string;
  name: string;
  store_id: number;
  store_name: string;
  days_in_stock: number;
  quantity: number;
};

export type AnalyticsAging = {
  items: AgingMetric[];
};

export type StockoutForecastMetric = {
  device_id: number;
  sku: string;
  name: string;
  store_id: number;
  store_name: string;
  average_daily_sales: number;
  projected_days: number | null;
  quantity: number;
  trend: string;
  trend_score: number;
  confidence: number;
  alert_level: string | null;
  sold_units: number;
};

export type AnalyticsForecast = {
  items: StockoutForecastMetric[];
};

export type StoreComparativeMetric = {
  store_id: number;
  store_name: string;
  device_count: number;
  total_units: number;
  inventory_value: number;
  average_rotation: number;
  average_aging_days: number;
  sales_last_30_days: number;
  sales_count_last_30_days: number;
};

export type AnalyticsComparative = {
  items: StoreComparativeMetric[];
};

export type ProfitMarginMetric = {
  store_id: number;
  store_name: string;
  revenue: number;
  cost: number;
  profit: number;
  margin_percent: number;
};

export type AnalyticsProfitMargin = {
  items: ProfitMarginMetric[];
};

export type SalesProjectionMetric = {
  store_id: number;
  store_name: string;
  average_daily_units: number;
  average_ticket: number;
  projected_units: number;
  projected_revenue: number;
  confidence: number;
  trend: string;
  trend_score: number;
  revenue_trend_score: number;
  r2_revenue: number;
};

export type AnalyticsSalesProjection = {
  items: SalesProjectionMetric[];
};

export type AnalyticsAlert = {
  type: string;
  level: string;
  message: string;
  store_id: number | null;
  store_name: string;
  device_id: number | null;
  sku: string | null;
};

export type AnalyticsAlerts = {
  items: AnalyticsAlert[];
};

export type RiskMetric = {
  total: number;
  average: number;
  maximum: number;
  last_seen?: string | null;
};

export type RiskAlert = {
  code: string;
  title: string;
  description: string;
  severity: "info" | "media" | "alta" | "critica";
  occurrences: number;
  detail?: Record<string, unknown> | null;
};

export type RiskAlertsResponse = {
  generated_at: string;
  alerts: RiskAlert[];
  metrics: Record<string, RiskMetric>;
};

export type PurchaseSupplierMetric = {
  store_id: number;
  store_name: string;
  supplier: string;
  device_count: number;
  total_ordered: number;
  total_received: number;
  pending_backorders: number;
  total_cost: number;
  average_unit_cost: number;
  average_rotation: number;
  average_days_in_stock: number;
  last_purchase_at: string | null;
};

export type PurchaseAnalytics = {
  items: PurchaseSupplierMetric[];
};

export type StoreRealtimeWidget = {
  store_id: number;
  store_name: string;
  inventory_value: number;
  sales_today: number;
  last_sale_at: string | null;
  low_stock_devices: number;
  pending_repairs: number;
  last_sync_at: string | null;
  trend: string;
  trend_score: number;
  confidence: number;
};

export type AnalyticsRealtime = {
  items: StoreRealtimeWidget[];
};

export type AnalyticsCategories = {
  categories: string[];
};

export type AnalyticsFilters = {
  storeIds?: number[];
  dateFrom?: string;
  dateTo?: string;
  category?: string;
  supplier?: string;
};

function buildAnalyticsQuery(filters?: AnalyticsFilters): string {
  if (!filters) {
    return "";
  }
  const params = new URLSearchParams();
  if (filters.storeIds && filters.storeIds.length > 0) {
    filters.storeIds.forEach((id) => {
      params.append("store_ids", String(id));
    });
  }
  if (filters.dateFrom) {
    params.set("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.set("date_to", filters.dateTo);
  }
  if (filters.category) {
    params.set("category", filters.category);
  }
  if (filters.supplier) {
    params.set("supplier", filters.supplier);
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function getRotationAnalytics(
  token: string,
  filters?: AnalyticsFilters,
): Promise<AnalyticsRotation> {
  const query = buildAnalyticsQuery(filters);
  return request<AnalyticsRotation>(`/reports/analytics/rotation${query}`, { method: "GET" }, token);
}

export function getAgingAnalytics(
  token: string,
  filters?: AnalyticsFilters,
): Promise<AnalyticsAging> {
  const query = buildAnalyticsQuery(filters);
  return request<AnalyticsAging>(`/reports/analytics/aging${query}`, { method: "GET" }, token);
}

export function getForecastAnalytics(
  token: string,
  filters?: AnalyticsFilters,
): Promise<AnalyticsForecast> {
  const query = buildAnalyticsQuery(filters);
  return request<AnalyticsForecast>(`/reports/analytics/stockout_forecast${query}`, { method: "GET" }, token);
}

export async function downloadAnalyticsPdf(
  token: string,
  reason: string,
  filters?: AnalyticsFilters,
): Promise<void> {
  const query = buildAnalyticsQuery(filters);
  const response = await fetch(`${API_URL}/reports/analytics/pdf${query}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible descargar el PDF analítico");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_analytics.pdf";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function downloadAnalyticsCsv(
  token: string,
  reason: string,
  filters?: AnalyticsFilters,
): Promise<void> {
  const query = buildAnalyticsQuery(filters);
  const response = await fetch(`${API_URL}/reports/analytics/export.csv${query}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible descargar el CSV analítico");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_analytics.csv";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function getComparativeAnalytics(
  token: string,
  filters?: AnalyticsFilters,
): Promise<AnalyticsComparative> {
  const query = buildAnalyticsQuery(filters);
  return request<AnalyticsComparative>(`/reports/analytics/comparative${query}`, { method: "GET" }, token);
}

export function getProfitMarginAnalytics(
  token: string,
  filters?: AnalyticsFilters,
): Promise<AnalyticsProfitMargin> {
  const query = buildAnalyticsQuery(filters);
  return request<AnalyticsProfitMargin>(`/reports/analytics/profit_margin${query}`, { method: "GET" }, token);
}

export function getSalesProjectionAnalytics(
  token: string,
  filters?: AnalyticsFilters,
): Promise<AnalyticsSalesProjection> {
  const query = buildAnalyticsQuery(filters);
  return request<AnalyticsSalesProjection>(`/reports/analytics/sales_forecast${query}`, { method: "GET" }, token);
}

export function getAnalyticsCategories(token: string): Promise<AnalyticsCategories> {
  return request<AnalyticsCategories>("/reports/analytics/categories", { method: "GET" }, token);
}

export function getAnalyticsAlerts(
  token: string,
  filters?: AnalyticsFilters,
): Promise<AnalyticsAlerts> {
  const query = buildAnalyticsQuery(filters);
  return request<AnalyticsAlerts>(`/reports/analytics/alerts${query}`, { method: "GET" }, token);
}

export function getRiskAlerts(
  token: string,
  filters?: { dateFrom?: string; dateTo?: string; discountThreshold?: number; cancellationThreshold?: number },
): Promise<RiskAlertsResponse> {
  const params = new URLSearchParams();
  if (filters?.dateFrom) {
    params.set("date_from", filters.dateFrom);
  }
  if (filters?.dateTo) {
    params.set("date_to", filters.dateTo);
  }
  if (typeof filters?.discountThreshold === "number") {
    params.set("discount_threshold", String(filters.discountThreshold));
  }
  if (typeof filters?.cancellationThreshold === "number") {
    params.set("cancellation_threshold", String(filters.cancellationThreshold));
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<RiskAlertsResponse>(`/reports/analytics/risk${suffix}`, { method: "GET" }, token);
}

export function getAnalyticsRealtime(
  token: string,
  filters?: AnalyticsFilters,
): Promise<AnalyticsRealtime> {
  const query = buildAnalyticsQuery(filters);
  return request<AnalyticsRealtime>(`/reports/analytics/realtime${query}`, { method: "GET" }, token);
}

export function getPurchaseAnalytics(
  token: string,
  filters?: AnalyticsFilters,
): Promise<PurchaseAnalytics> {
  const query = buildAnalyticsQuery(filters);
  return request<PurchaseAnalytics>(`/reports/purchases${query}`, { method: "GET" }, token);
}
