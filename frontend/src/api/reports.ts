import { httpClient } from "@api/http";
import { SystemLogLevel } from "./types";
import { request, API_URL } from "./client";

export type GlobalReportLogEntry = {
  id_log: number;
  usuario?: string | null;
  modulo: string;
  accion: string;
  descripcion: string;
  fecha: string;
  nivel: SystemLogLevel;
  ip_origen?: string | null;
};

export type GlobalReportErrorEntry = {
  id_error: number;
  mensaje: string;
  stack_trace?: string | null;
  modulo: string;
  fecha: string;
  usuario?: string | null;
};

export type GlobalReportAlert = {
  type: "critical_log" | "system_error" | "sync_failure";
  level: SystemLogLevel;
  message: string;
  module?: string | null;
  occurred_at?: string | null;
  reference?: string | null;
  count: number;
};

export type GlobalReportBreakdownItem = {
  name: string;
  total: number;
};

export type GlobalReportTotals = {
  logs: number;
  errors: number;
  info: number;
  warning: number;
  error: number;
  critical: number;
  sync_pending: number;
  sync_failed: number;
  last_activity_at?: string | null;
};

export type GlobalReportFiltersState = {
  date_from?: string | null;
  date_to?: string | null;
  module?: string | null;
  severity?: SystemLogLevel | null;
};

export type GlobalReportOverview = {
  generated_at: string;
  filters: GlobalReportFiltersState;
  totals: GlobalReportTotals;
  module_breakdown: GlobalReportBreakdownItem[];
  severity_breakdown: GlobalReportBreakdownItem[];
  recent_logs: GlobalReportLogEntry[];
  recent_errors: GlobalReportErrorEntry[];
  alerts: GlobalReportAlert[];
};

export type GlobalReportSeriesPoint = {
  date: string;
  info: number;
  warning: number;
  error: number;
  critical: number;
  system_errors: number;
};

export type GlobalReportDashboard = {
  generated_at: string;
  filters: GlobalReportFiltersState;
  activity_series: GlobalReportSeriesPoint[];
  module_distribution: GlobalReportBreakdownItem[];
  severity_distribution: GlobalReportBreakdownItem[];
};

export type GlobalReportFilters = {
  dateFrom?: string;
  dateTo?: string;
  module?: string;
  severity?: SystemLogLevel;
};

function buildGlobalReportQuery(filters: GlobalReportFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.dateFrom) {
    params.set("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.set("date_to", filters.dateTo);
  }
  if (filters.module) {
    params.set("module", filters.module);
  }
  if (filters.severity) {
    params.set("severity", filters.severity);
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function getGlobalReportOverview(
  token: string,
  filters: GlobalReportFilters = {},
): Promise<GlobalReportOverview> {
  const query = buildGlobalReportQuery(filters);
  return request<GlobalReportOverview>(`/reports/global/overview${query}`, { method: "GET" }, token);
}

export function getGlobalReportDashboard(
  token: string,
  filters: GlobalReportFilters = {},
): Promise<GlobalReportDashboard> {
  const query = buildGlobalReportQuery(filters);
  return request<GlobalReportDashboard>(`/reports/global/dashboard${query}`, { method: "GET" }, token);
}

export async function downloadGlobalReportPdf(
  token: string,
  reason: string,
  filters: GlobalReportFilters = {},
): Promise<void> {
  const query = buildGlobalReportQuery(filters);
  const suffix = query ? `${query}&format=pdf` : "?format=pdf";
  const response = await fetch(`${API_URL}/reports/global/export${suffix}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible descargar el PDF de reportes globales");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_reporte_global.pdf";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function downloadGlobalReportXlsx(
  token: string,
  reason: string,
  filters: GlobalReportFilters = {},
): Promise<void> {
  const query = buildGlobalReportQuery(filters);
  const suffix = query ? `${query}&format=xlsx` : "?format=xlsx";
  const response = await fetch(`${API_URL}/reports/global/export${suffix}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible descargar el Excel de reportes globales");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_reporte_global.xlsx";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function downloadGlobalReportCsv(
  token: string,
  reason: string,
  filters: GlobalReportFilters = {},
): Promise<void> {
  const query = buildGlobalReportQuery(filters);
  const suffix = query ? `${query}&format=csv` : "?format=csv";
  const response = await fetch(`${API_URL}/reports/global/export${suffix}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible descargar el CSV de reportes globales");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_reporte_global.csv";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// Sales Reports

export type SalesSummaryReport = {
  totalSales: number;
  totalOrders: number;
  avgTicket: number;
  returnsCount: number;
  net: number;
};

export type CashCloseReport = {
  closingSuggested: number;
  refunds: number;
};

export type SalesByProductItem = {
  sku: string;
  name: string;
  qty: number;
  gross: number;
  net: number;
};

export type SalesReportFilters = {
  branchId?: number;
  from?: string;
  to?: string;
  limit?: number;
};

export async function fetchSalesSummary(filters: SalesReportFilters = {}): Promise<SalesSummaryReport> {
  const params = {
    store_id: filters.branchId,
    date_from: filters.from,
    date_to: filters.to,
  };
  const response = await httpClient.get("/reports/sales/summary", { params });
  const data = response.data;
  return {
    totalSales: data.total_sales ?? 0,
    totalOrders: data.total_transactions ?? 0,
    avgTicket: data.average_ticket ?? 0,
    returnsCount: data.returns_count ?? 0,
    net: data.net_sales ?? data.total_sales ?? 0,
  };
}

export async function fetchCashCloseReport(filters: SalesReportFilters = {}): Promise<CashCloseReport> {
  const params = {
    store_id: filters.branchId,
    date_from: filters.from,
    date_to: filters.to,
  };
  const response = await httpClient.get("/reports/sales/cash-close", { params });
  const data = response.data;
  return {
    closingSuggested: data.closing_suggested ?? data.expected_amount ?? 0,
    refunds: data.refunds ?? 0,
  };
}

export async function fetchSalesByProduct(filters: SalesReportFilters = {}): Promise<SalesByProductItem[]> {
  const params = {
    store_id: filters.branchId,
    date_from: filters.from,
    date_to: filters.to,
    limit: filters.limit,
  };
  const response = await httpClient.get("/reports/sales/by-product", { params });
  const items = Array.isArray(response.data) ? response.data : response.data.items || [];
  return items.map((item: any) => ({
    sku: item.sku,
    name: item.name,
    qty: item.quantity ?? item.qty ?? 0,
    gross: item.total ?? item.gross ?? 0,
    net: item.profit ?? item.net ?? 0,
  }));
}
