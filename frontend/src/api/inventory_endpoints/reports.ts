import { request } from "../client";
import { triggerDownload } from "../client";
import {
  InventoryCurrentFilters,
  InventoryCurrentReport,
  InventoryValueFilters,
  InventoryValueReport,
  InventoryTopProductsFilters,
  TopProductsReport,
  InactiveProductsFilters,
  InactiveProductsReport,
  SyncDiscrepancyFilters,
  SyncDiscrepancyReport,
  InventoryAuditFilters
} from "../inventoryTypes";
import { buildInventoryValueParams, appendNumericList } from "./utils";

function buildInventoryAuditParams(filters: InventoryAuditFilters = {}): URLSearchParams {
  const params = new URLSearchParams();
  if (typeof filters.performedById === "number") {
    params.append("performed_by_id", String(filters.performedById));
  }
  if (filters.dateFrom) {
    params.append("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.append("date_to", filters.dateTo);
  }
  if (typeof filters.limit === "number") {
    params.append("limit", String(filters.limit));
  }
  if (typeof filters.offset === "number") {
    params.append("offset", String(filters.offset));
  }
  return params;
}

function buildTopProductsParams(filters: InventoryTopProductsFilters = {}): URLSearchParams {
  const params = buildInventoryValueParams(filters);
  if (filters.dateFrom) {
    params.append("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.append("date_to", filters.dateTo);
  }
  if (typeof filters.limit === "number") {
    params.append("limit", String(filters.limit));
  }
  return params;
}

function buildInactiveProductsParams(filters: InactiveProductsFilters = {}): URLSearchParams {
  const params = buildInventoryValueParams(filters);
  if (
    typeof filters.minDaysWithoutMovement === "number"
    && Number.isFinite(filters.minDaysWithoutMovement)
  ) {
    params.append(
      "min_days_without_movement",
      String(Math.max(Math.floor(filters.minDaysWithoutMovement), 0)),
    );
  }
  if (typeof filters.limit === "number" && Number.isFinite(filters.limit)) {
    params.append("limit", String(Math.max(Math.floor(filters.limit), 1)));
  }
  if (typeof filters.offset === "number" && Number.isFinite(filters.offset)) {
    params.append("offset", String(Math.max(Math.floor(filters.offset), 0)));
  }
  return params;
}

function buildSyncDiscrepancyParams(filters: SyncDiscrepancyFilters = {}): URLSearchParams {
  const params = new URLSearchParams();
  appendNumericList(params, "store_ids", filters.storeIds);
  if (filters.dateFrom) {
    params.append("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.append("date_to", filters.dateTo);
  }
  if (filters.severity) {
    params.append("severity", filters.severity);
  }
  if (typeof filters.minDifference === "number" && Number.isFinite(filters.minDifference)) {
    params.append("min_difference", String(Math.max(Math.floor(filters.minDifference), 0)));
  }
  if (typeof filters.limit === "number" && Number.isFinite(filters.limit)) {
    params.append("limit", String(Math.max(Math.floor(filters.limit), 1)));
  }
  if (typeof filters.offset === "number" && Number.isFinite(filters.offset)) {
    params.append("offset", String(Math.max(Math.floor(filters.offset), 0)));
  }
  return params;
}

export function getInventoryCurrentReport(
  token: string,
  filters: InventoryCurrentFilters = {},
): Promise<InventoryCurrentReport> {
  const params = new URLSearchParams();
  appendNumericList(params, "store_ids", filters.storeIds);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<InventoryCurrentReport>(`/reports/inventory/current${suffix}`, { method: "GET" }, token);
}

export function getInventoryValueReport(
  token: string,
  filters: InventoryValueFilters = {},
): Promise<InventoryValueReport> {
  const params = buildInventoryValueParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<InventoryValueReport>(`/reports/inventory/value${suffix}`, { method: "GET" }, token);
}

export function getTopProductsReport(
  token: string,
  filters: InventoryTopProductsFilters = {},
): Promise<TopProductsReport> {
  const params = buildTopProductsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<TopProductsReport>(`/reports/inventory/top-products${suffix}`, { method: "GET" }, token);
}

export function getInactiveProductsReport(
  token: string,
  filters: InactiveProductsFilters = {},
): Promise<InactiveProductsReport> {
  const params = buildInactiveProductsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<InactiveProductsReport>(`/reports/inventory/inactive-products${suffix}`, { method: "GET" }, token);
}

export function getSyncDiscrepancyReport(
  token: string,
  filters: SyncDiscrepancyFilters = {},
): Promise<SyncDiscrepancyReport> {
  const params = buildSyncDiscrepancyParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<SyncDiscrepancyReport>(`/reports/inventory/sync-discrepancies${suffix}`, { method: "GET" }, token);
}

export async function downloadInventoryPdf(token: string, reason: string): Promise<void> {
  const blob = await request<Blob>(
    "/reports/inventory/pdf",
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
  triggerDownload(blob, "inventario.pdf");
}

export async function downloadInventoryCsv(token: string, reason: string): Promise<void> {
  const blob = await request<Blob>(
    "/reports/inventory/csv",
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
  triggerDownload(blob, "inventario.csv");
}

export async function downloadInventoryCurrentCsv(
  token: string,
  filters: InventoryCurrentFilters,
  reason: string,
): Promise<void> {
  const params = new URLSearchParams();
  appendNumericList(params, "store_ids", filters.storeIds);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const blob = await request<Blob>(
    `/reports/inventory/current/csv${suffix}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
  triggerDownload(blob, "inventario_actual.csv");
}

export async function downloadInventoryCurrentPdf(
  token: string,
  filters: InventoryCurrentFilters,
  reason: string,
): Promise<void> {
  const params = new URLSearchParams();
  appendNumericList(params, "store_ids", filters.storeIds);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const blob = await request<Blob>(
    `/reports/inventory/current/pdf${suffix}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
  triggerDownload(blob, "inventario_actual.pdf");
}

export async function downloadInventoryCurrentXlsx(
  token: string,
  filters: InventoryCurrentFilters,
  reason: string,
): Promise<void> {
  const params = new URLSearchParams();
  appendNumericList(params, "store_ids", filters.storeIds);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const blob = await request<Blob>(
    `/reports/inventory/current/xlsx${suffix}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
  triggerDownload(blob, "inventario_actual.xlsx");
}

export async function downloadInventoryValueCsv(
  token: string,
  filters: InventoryValueFilters,
  reason: string,
): Promise<void> {
  const params = buildInventoryValueParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const blob = await request<Blob>(
    `/reports/inventory/value/csv${suffix}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
  triggerDownload(blob, "valor_inventario.csv");
}

export async function downloadInventoryValuePdf(
  token: string,
  reason: string,
  filters: InventoryValueFilters = {},
): Promise<void> {
  const params = buildInventoryValueParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const blob = await request<Blob>(
    `/reports/inventory/value/pdf${suffix}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
  triggerDownload(blob, "valor_inventario.pdf");
}

export async function downloadInventoryValueXlsx(
  token: string,
  reason: string,
  filters: InventoryValueFilters = {},
): Promise<void> {
  const params = buildInventoryValueParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const blob = await request<Blob>(
    `/reports/inventory/value/xlsx${suffix}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
  triggerDownload(blob, "valor_inventario.xlsx");
}

export async function downloadInventoryAuditCsv(
  token: string,
  reason: string,
  filters: InventoryAuditFilters = {},
): Promise<void> {
  const params = buildInventoryAuditParams(filters);
  params.set("format", "csv");
  const query = params.toString();
  const blob = await request<Blob>(
    `/inventory/counts/audit/report?${query}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
  triggerDownload(blob, "auditoria_inventario.csv");
}

export async function downloadInventoryAuditPdf(
  token: string,
  reason: string,
  filters: InventoryAuditFilters = {},
): Promise<void> {
  const params = buildInventoryAuditParams(filters);
  params.set("format", "pdf");
  const query = params.toString();
  const blob = await request<Blob>(
    `/inventory/counts/audit/report?${query}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
  triggerDownload(blob, "auditoria_inventario.pdf");
}

export async function downloadTopProductsCsv(
  token: string,
  reason: string,
  filters: InventoryTopProductsFilters = {},
): Promise<void> {
  const params = buildTopProductsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const blob = await request<Blob>(
    `/reports/inventory/top-products/csv${suffix}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
  triggerDownload(blob, "top_productos.csv");
}

export async function downloadTopProductsPdf(
  token: string,
  reason: string,
  filters: InventoryTopProductsFilters = {},
): Promise<void> {
  const params = buildTopProductsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const blob = await request<Blob>(
    `/reports/inventory/top-products/pdf${suffix}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
  triggerDownload(blob, "top_productos.pdf");
}

export async function downloadTopProductsXlsx(
  token: string,
  reason: string,
  filters: InventoryTopProductsFilters = {},
): Promise<void> {
  const params = buildTopProductsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const blob = await request<Blob>(
    `/reports/inventory/top-products/xlsx${suffix}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
  triggerDownload(blob, "top_productos.xlsx");
}
