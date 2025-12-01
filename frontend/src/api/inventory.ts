import { request, requestCollection, API_URL, parseFilenameFromDisposition } from "./client";
import { PaginatedResponse } from "./types";
import { PosHardwareActionResponse } from "./pos";
import {
  DeviceIdentifier,
  DeviceIdentifierInput,
  Device,
  ProductVariant,
  ProductVariantCreateInput,
  ProductVariantUpdateInput,
  ProductBundleItem,
  ProductBundle,
  ProductBundleItemInput,
  ProductBundleCreateInput,
  ProductBundleUpdateInput,
  CatalogDevice,
  ImportValidation,
  ImportValidationDevice,
  ImportValidationDetail,
  ImportValidationSummary,
  DeviceUpdateInput,
  InventoryAvailabilityStore,
  InventoryAvailabilityRecord,
  InventoryAvailabilityResponse,
  Warehouse,
  WarehouseTransferInput,
  InventoryAvailabilityParams,
  MovementInput,
  InventoryMovement,
  MovementResponse,
  InventoryReservationState,
  InventoryReservation,
  InventoryReservationInput,
  InventoryReservationRenewInput,
  StoreValueMetric,
  LowStockDevice,
  DashboardPoint,
  DashboardReceivableCustomer,
  DashboardReceivableMetrics,
  DashboardSalesEntityMetric,
  DashboardSalesInsights,
  InventoryMetrics,
  InventoryAlertSeverity,
  InventoryAlertItem,
  InventoryAlertSummary,
  InventoryAlertSettings,
  InventoryAlertsResponse,
  SmartImportColumnMatch,
  InventorySmartImportPreview,
  InventorySmartImportResult,
  InventorySmartImportResponse,
  InventoryImportHistoryEntry,
  DeviceListFilters,
  InventoryCurrentFilters,
  InventoryValueFilters,
  InventoryMovementsFilters,
  InventoryAuditFilters,
  InventoryTopProductsFilters,
  InactiveProductsFilters,
  SyncBranchHealth,
  SyncConflictStoreDetail,
  SyncDiscrepancyLog,
  SyncDiscrepancyFilters,
  InventoryReceivingDistributionInput,
  InventoryReceivingLineInput,
  InventoryReceivingRequest,
  InventoryReceivingProcessed,
  InventoryReceivingResult,
  InventoryCountLineInput,
  InventoryCycleCountRequest,
  InventoryCountDiscrepancy,
  InventoryCycleCountResult,
  DeviceImportSummary,
  InventoryCurrentStoreReport,
  InventoryTotals,
  InventoryCurrentReport,
  MovementTypeSummary,
  MovementPeriodSummary,
  MovementReportEntry,
  InventoryMovementsSummary,
  InventoryMovementsReport,
  TopProductReportItem,
  TopProductsReport,
  InventoryValueStore,
  InventoryValueTotals,
  InventoryValueReport,
  InactiveProductEntry,
  InactiveProductsTotals,
  InactiveProductsReport,
  SyncDiscrepancyTotals,
  SyncDiscrepancyReport,
  MinimumStockAlert,
  MinimumStockSummary,
  MinimumStockAlertsResponse,
  DeviceSearchFilters,
  DeviceLabelFormat,
  DeviceLabelTemplate,
  LabelConnectorInput,
  DeviceLabelDownload,
  DeviceLabelCommands
} from "./inventoryTypes";

export type { PaginatedResponse };
export type {
  DeviceIdentifier,
  DeviceIdentifierInput,
  Device,
  ProductVariant,
  ProductVariantCreateInput,
  ProductVariantUpdateInput,
  ProductBundleItem,
  ProductBundle,
  ProductBundleItemInput,
  ProductBundleCreateInput,
  ProductBundleUpdateInput,
  CatalogDevice,
  ImportValidation,
  ImportValidationDevice,
  ImportValidationDetail,
  ImportValidationSummary,
  DeviceUpdateInput,
  InventoryAvailabilityStore,
  InventoryAvailabilityRecord,
  InventoryAvailabilityResponse,
  Warehouse,
  WarehouseTransferInput,
  InventoryAvailabilityParams,
  MovementInput,
  InventoryMovement,
  MovementResponse,
  InventoryReservationState,
  InventoryReservation,
  InventoryReservationInput,
  InventoryReservationRenewInput,
  StoreValueMetric,
  LowStockDevice,
  DashboardPoint,
  DashboardReceivableCustomer,
  DashboardReceivableMetrics,
  DashboardSalesEntityMetric,
  DashboardSalesInsights,
  InventoryMetrics,
  InventoryAlertSeverity,
  InventoryAlertItem,
  InventoryAlertSummary,
  InventoryAlertSettings,
  InventoryAlertsResponse,
  SmartImportColumnMatch,
  InventorySmartImportPreview,
  InventorySmartImportResult,
  InventorySmartImportResponse,
  InventoryImportHistoryEntry,
  DeviceListFilters,
  InventoryCurrentFilters,
  InventoryValueFilters,
  InventoryMovementsFilters,
  InventoryAuditFilters,
  InventoryTopProductsFilters,
  InactiveProductsFilters,
  SyncBranchHealth,
  SyncConflictStoreDetail,
  SyncDiscrepancyLog,
  SyncDiscrepancyFilters,
  InventoryReceivingDistributionInput,
  InventoryReceivingLineInput,
  InventoryReceivingRequest,
  InventoryReceivingProcessed,
  InventoryReceivingResult,
  InventoryCountLineInput,
  InventoryCycleCountRequest,
  InventoryCountDiscrepancy,
  InventoryCycleCountResult,
  DeviceImportSummary,
  InventoryCurrentStoreReport,
  InventoryTotals,
  InventoryCurrentReport,
  MovementTypeSummary,
  MovementPeriodSummary,
  MovementReportEntry,
  InventoryMovementsSummary,
  InventoryMovementsReport,
  TopProductReportItem,
  TopProductsReport,
  InventoryValueStore,
  InventoryValueTotals,
  InventoryValueReport,
  InactiveProductEntry,
  InactiveProductsTotals,
  InactiveProductsReport,
  SyncDiscrepancyTotals,
  SyncDiscrepancyReport,
  MinimumStockAlert,
  MinimumStockSummary,
  MinimumStockAlertsResponse,
  DeviceSearchFilters,
  DeviceLabelFormat,
  DeviceLabelTemplate,
  LabelConnectorInput,
  DeviceLabelDownload,
  DeviceLabelCommands
};

function appendNumericList(params: URLSearchParams, key: string, values?: number[]): void {
  if (!values) {
    return;
  }
  for (const value of values) {
    params.append(key, String(value));
  }
}

function appendStringList(params: URLSearchParams, key: string, values?: string[]): void {
  if (!values) {
    return;
  }
  for (const value of values) {
    if (value) {
      params.append(key, value);
    }
  }
}

function buildDeviceFilterParams(filters: DeviceListFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.search) {
    params.append("search", filters.search);
  }
  if (filters.estado) {
    params.append("estado", filters.estado);
  }
  if (filters.categoria) {
    params.append("categoria", filters.categoria);
  }
  if (filters.condicion) {
    params.append("condicion", filters.condicion);
  }
  if (filters.estado_inventario) {
    params.append("estado_inventario", filters.estado_inventario);
  }
  if (filters.ubicacion) {
    params.append("ubicacion", filters.ubicacion);
  }
  if (filters.proveedor) {
    params.append("proveedor", filters.proveedor);
  }
  if (filters.warehouse_id != null) {
    params.append("warehouse_id", String(filters.warehouse_id));
  }
  if (filters.fecha_ingreso_desde) {
    params.append("fecha_ingreso_desde", filters.fecha_ingreso_desde);
  }
  if (filters.fecha_ingreso_hasta) {
    params.append("fecha_ingreso_hasta", filters.fecha_ingreso_hasta);
  }
  if (typeof filters.limit === "number") {
    params.append("limit", String(filters.limit));
  }
  return params;
}

function buildInventoryValueParams(filters: InventoryValueFilters = {}): URLSearchParams {
  const params = new URLSearchParams();
  appendNumericList(params, "store_ids", filters.storeIds);
  appendStringList(params, "categories", filters.categories);
  return params;
}

function buildInventoryMovementsParams(filters: InventoryMovementsFilters = {}): URLSearchParams {
  const params = buildInventoryValueParams(filters);
  if (filters.dateFrom) {
    params.append("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.append("date_to", filters.dateTo);
  }
  if (filters.movementType) {
    params.append("movement_type", filters.movementType);
  }
  return params;
}

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

export function getDevices(
  token: string,
  storeId: number,
  filters: DeviceListFilters = {}
): Promise<Device[]> {
  const params = buildDeviceFilterParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return requestCollection<Device>(`/stores/${storeId}/devices${suffix}`, { method: "GET" }, token);
}

export function updateDevice(
  token: string,
  storeId: number,
  deviceId: number,
  payload: DeviceUpdateInput,
  reason: string
): Promise<Device> {
  return request<Device>(
    `/inventory/stores/${storeId}/devices/${deviceId}`,
    { method: "PATCH", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function getIncompleteDevices(
  token: string,
  storeId?: number,
  limit = 100,
): Promise<Device[]> {
  const params = new URLSearchParams();
  if (storeId != null) {
    params.set("store_id", String(storeId));
  }
  params.set("limit", String(limit));
  const query = params.toString();
  const url = query ? `/inventory/devices/incomplete?${query}` : "/inventory/devices/incomplete";
  return requestCollection<Device>(url, { method: "GET" }, token);
}

export function getInventoryAvailability(
  token: string,
  params: InventoryAvailabilityParams = {},
): Promise<InventoryAvailabilityResponse> {
  const queryParams = new URLSearchParams();
  if (params.query) {
    queryParams.set("query", params.query);
  }
  if (params.skus && params.skus.length > 0) {
    queryParams.set("skus", params.skus.join(","));
  }
  if (params.deviceIds && params.deviceIds.length > 0) {
    queryParams.set("device_ids", params.deviceIds.join(","));
  }
  if (params.limit) {
    queryParams.set("limit", String(params.limit));
  }
  const suffix = queryParams.toString() ? `?${queryParams.toString()}` : "";
  return request<InventoryAvailabilityResponse>(
    `/inventory/availability${suffix}`,
    { method: "GET" },
    token,
  );
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

export function getInventoryMovementsReport(
  token: string,
  filters: InventoryMovementsFilters = {},
): Promise<InventoryMovementsReport> {
  const params = buildInventoryMovementsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<InventoryMovementsReport>(`/reports/inventory/movements${suffix}`, { method: "GET" }, token);
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

export function getInventoryReservations(
  token: string,
  params: {
    storeId?: number;
    deviceId?: number;
    status?: InventoryReservationState;
    includeExpired?: boolean;
    page?: number;
    size?: number;
    limit?: number;
    offset?: number;
  } = {},
): Promise<PaginatedResponse<InventoryReservation>> {
  const queryParams = new URLSearchParams();
  if (typeof params.storeId === "number") {
    queryParams.set("store_id", String(params.storeId));
  }
  if (typeof params.deviceId === "number") {
    queryParams.set("device_id", String(params.deviceId));
  }
  if (params.status) {
    queryParams.set("status_filter", params.status);
  }
  if (params.includeExpired) {
    queryParams.set("include_expired", "true");
  }
  if (typeof params.page === "number") {
    queryParams.set("page", String(params.page));
  }
  if (typeof params.size === "number") {
    queryParams.set("size", String(params.size));
  }
  if (typeof params.limit === "number") {
    queryParams.set("limit", String(params.limit));
  }
  if (typeof params.offset === "number") {
    queryParams.set("offset", String(params.offset));
  }
  const suffix = queryParams.toString() ? `?${queryParams.toString()}` : "";
  return request<PaginatedResponse<InventoryReservation>>(
    `/inventory/reservations${suffix}`,
    { method: "GET" },
    token,
  );
}

export function createInventoryReservation(
  token: string,
  payload: InventoryReservationInput,
  reason: string,
): Promise<InventoryReservation> {
  return request<InventoryReservation>(
    "/inventory/reservations",
    {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Reason": reason },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function renewInventoryReservation(
  token: string,
  reservationId: number,
  payload: InventoryReservationRenewInput,
  reason: string,
): Promise<InventoryReservation> {
  return request<InventoryReservation>(
    `/inventory/reservations/${reservationId}/renew`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json", "X-Reason": reason },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function cancelInventoryReservation(
  token: string,
  reservationId: number,
  reason: string,
): Promise<InventoryReservation> {
  return request<InventoryReservation>(
    `/inventory/reservations/${reservationId}/cancel`,
    {
      method: "POST",
      headers: { "X-Reason": reason },
    },
    token,
  );
}

export function smartInventoryImport(
  token: string,
  file: File,
  reason: string,
  options: { overrides?: Record<string, string> } = {},
): Promise<InventorySmartImportResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (options.overrides && Object.keys(options.overrides).length > 0) {
    formData.append("overrides", JSON.stringify(options.overrides));
  }
  return request<InventorySmartImportResponse>(
    "/inventory/import/smart",
    { method: "POST", body: formData, headers: { "X-Reason": reason } },
    token,
  );
}

export function getSmartImportHistory(
  token: string,
  limit = 10,
): Promise<InventoryImportHistoryEntry[]> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  return requestCollection<InventoryImportHistoryEntry>(
    `/inventory/import/smart/history?${params.toString()}`,
    { method: "GET" },
    token,
  );
}

export function getImportValidationReport(token: string): Promise<ImportValidationSummary> {
  return request<ImportValidationSummary>("/validacion/reporte", { method: "GET" }, token);
}

export function getPendingImportValidations(
  token: string,
  limit = 200,
): Promise<ImportValidationDetail[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  return requestCollection<ImportValidationDetail>(
    `/validacion/pendientes?${params.toString()}`,
    { method: "GET" },
    token,
  );
}

export function markImportValidationCorrected(
  token: string,
  validationId: number,
  reason: string,
): Promise<ImportValidation> {
  return request<ImportValidation>(
    `/validacion/${validationId}/corregir`,
    { method: "PATCH", headers: { "X-Reason": reason } },
    token,
  );
}

export async function downloadInventoryPdf(token: string, reason: string): Promise<void> {
  await request<Blob>(
    "/reports/inventory/pdf",
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export async function downloadInventoryCsv(token: string, reason: string): Promise<void> {
  await request<Blob>(
    "/reports/inventory/csv",
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
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
  await request<Blob>(
    `/reports/inventory/current/csv${suffix}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
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
  await request<Blob>(
    `/reports/inventory/current/pdf${suffix}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
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
  await request<Blob>(
    `/reports/inventory/current/xlsx${suffix}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export async function downloadInventoryValueCsv(
  token: string,
  filters: InventoryValueFilters,
  reason: string,
): Promise<void> {
  const params = buildInventoryValueParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  await request<Blob>(
    `/reports/inventory/value/csv${suffix}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export async function downloadInventoryValuePdf(
  token: string,
  reason: string,
  filters: InventoryValueFilters = {},
): Promise<void> {
  const params = buildInventoryValueParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  await request<Blob>(
    `/reports/inventory/value/pdf${suffix}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export async function downloadInventoryValueXlsx(
  token: string,
  reason: string,
  filters: InventoryValueFilters = {},
): Promise<void> {
  const params = buildInventoryValueParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  await request<Blob>(
    `/reports/inventory/value/xlsx${suffix}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export async function downloadInventoryMovementsCsv(
  token: string,
  reason: string,
  filters: InventoryMovementsFilters = {},
): Promise<void> {
  const params = buildInventoryMovementsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  await request<Blob>(
    `/reports/inventory/movements/csv${suffix}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export async function downloadInventoryMovementsPdf(
  token: string,
  reason: string,
  filters: InventoryMovementsFilters = {},
): Promise<void> {
  const params = buildInventoryMovementsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  await request<Blob>(
    `/reports/inventory/movements/pdf${suffix}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export async function downloadInventoryMovementsXlsx(
  token: string,
  reason: string,
  filters: InventoryMovementsFilters = {},
): Promise<void> {
  const params = buildInventoryMovementsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  await request<Blob>(
    `/reports/inventory/movements/xlsx${suffix}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export async function downloadInventoryAdjustmentsCsv(
  token: string,
  reason: string,
  filters: InventoryMovementsFilters = {},
): Promise<void> {
  const params = buildInventoryMovementsParams(filters);
  params.set("format", "csv");
  const query = params.toString();
  await request<Blob>(
    `/inventory/counts/adjustments/report?${query}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export async function downloadInventoryAdjustmentsPdf(
  token: string,
  reason: string,
  filters: InventoryMovementsFilters = {},
): Promise<void> {
  const params = buildInventoryMovementsParams(filters);
  params.set("format", "pdf");
  const query = params.toString();
  await request<Blob>(
    `/inventory/counts/adjustments/report?${query}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export async function downloadInventoryAuditCsv(
  token: string,
  reason: string,
  filters: InventoryAuditFilters = {},
): Promise<void> {
  const params = buildInventoryAuditParams(filters);
  params.set("format", "csv");
  const query = params.toString();
  await request<Blob>(
    `/inventory/counts/audit/report?${query}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export async function downloadInventoryAuditPdf(
  token: string,
  reason: string,
  filters: InventoryAuditFilters = {},
): Promise<void> {
  const params = buildInventoryAuditParams(filters);
  params.set("format", "pdf");
  const query = params.toString();
  await request<Blob>(
    `/inventory/counts/audit/report?${query}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export async function downloadTopProductsCsv(
  token: string,
  reason: string,
  filters: InventoryTopProductsFilters = {},
): Promise<void> {
  const params = buildTopProductsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  await request<Blob>(
    `/reports/inventory/top-products/csv${suffix}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export async function downloadTopProductsPdf(
  token: string,
  reason: string,
  filters: InventoryTopProductsFilters = {},
): Promise<void> {
  const params = buildTopProductsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  await request<Blob>(
    `/reports/inventory/top-products/pdf${suffix}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export async function downloadTopProductsXlsx(
  token: string,
  reason: string,
  filters: InventoryTopProductsFilters = {},
): Promise<void> {
  const params = buildTopProductsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  await request<Blob>(
    `/reports/inventory/top-products/xlsx${suffix}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export async function exportStoreDevicesCsv(
  token: string,
  storeId: number,
  filters: DeviceListFilters,
  reason: string,
): Promise<void> {
  const params = buildDeviceFilterParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  await request<Blob>(
    `/inventory/stores/${storeId}/devices/export${suffix}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export function importStoreDevicesCsv(
  token: string,
  storeId: number,
  file: File,
  reason: string,
): Promise<InventorySmartImportResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request<InventorySmartImportResponse>(
    `/inventory/stores/${storeId}/devices/import`,
    { method: "POST", body: formData, headers: { "X-Reason": reason } },
    token,
  );
}

function buildDeviceSearchFilterParams(filters: DeviceSearchFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.imei) params.append("imei", filters.imei);
  if (filters.serial) params.append("serial", filters.serial);
  if (filters.capacidad_gb !== undefined) params.append("capacidad_gb", String(filters.capacidad_gb));
  if (filters.color) params.append("color", filters.color);
  if (filters.marca) params.append("marca", filters.marca);
  if (filters.modelo) params.append("modelo", filters.modelo);
  if (filters.categoria) params.append("categoria", filters.categoria);
  if (filters.condicion) params.append("condicion", filters.condicion);
  if (filters.estado_comercial) params.append("estado_comercial", filters.estado_comercial);
  if (filters.estado) params.append("estado", filters.estado);
  if (filters.ubicacion) params.append("ubicacion", filters.ubicacion);
  if (filters.proveedor) params.append("proveedor", filters.proveedor);
  if (filters.fecha_ingreso_desde) params.append("fecha_ingreso_desde", filters.fecha_ingreso_desde);
  if (filters.fecha_ingreso_hasta) params.append("fecha_ingreso_hasta", filters.fecha_ingreso_hasta);
  return params;
}

export async function searchCatalogDevices(
  token: string,
  filters: DeviceSearchFilters,
  limit = 20,
): Promise<CatalogDevice[]> {
  const params = buildDeviceSearchFilterParams(filters);
  params.set("limit", String(limit));
  const response = await request<PaginatedResponse<CatalogDevice>>(
    `/inventory/devices/search?${params.toString()}`,
    { method: "GET" },
    token,
  );
  return response.items;
}

export function getDeviceIdentifier(
  token: string,
  storeId: number,
  deviceId: number,
): Promise<DeviceIdentifier> {
  return request<DeviceIdentifier>(
    `/inventory/stores/${storeId}/devices/${deviceId}/identifier`,
    { method: "GET" },
    token,
  );
}

export function upsertDeviceIdentifier(
  token: string,
  storeId: number,
  deviceId: number,
  payload: DeviceIdentifierInput,
  reason: string,
): Promise<DeviceIdentifier> {
  return request<DeviceIdentifier>(
    `/inventory/stores/${storeId}/devices/${deviceId}/identifier`,
    { method: "PUT", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token,
  );
}

export async function requestDeviceLabel(
  token: string,
  storeId: number,
  deviceId: number,
  reason: string,
  options: {
    format?: DeviceLabelFormat;
    template?: DeviceLabelTemplate;
    printerName?: string | null;
  } = {},
): Promise<DeviceLabelDownload | DeviceLabelCommands> {
  const format = options.format ?? "pdf";
  const template = options.template ?? "38x25";
  const url = new URL(
    `${API_URL}/inventory/stores/${storeId}/devices/${deviceId}/label/${format}`,
  );
  url.searchParams.set("template", template);
  if (options.printerName) {
    url.searchParams.set("printer_name", options.printerName);
  }

  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    "X-Reason": reason,
  };
  headers.Accept = format === "pdf" ? "application/pdf" : "application/json";

  const response = await fetch(url.toString(), {
    method: "GET",
    headers,
  });

  if (!response.ok) {
    throw new Error("No fue posible generar la etiqueta del dispositivo.");
  }

  if (format === "pdf") {
    const blob = await response.blob();
    const disposition = response.headers.get("content-disposition");
    const fallback = `etiqueta_${storeId}_${deviceId}.pdf`;
    const filename = parseFilenameFromDisposition(disposition, fallback);
    return { blob, filename };
  }

  const payload = (await response.json()) as DeviceLabelCommands;
  return payload;
}

export async function triggerDeviceLabelPrint(
  token: string,
  storeId: number,
  deviceId: number,
  reason: string,
  payload: { format: DeviceLabelFormat; template: DeviceLabelTemplate; connector?: LabelConnectorInput | null },
): Promise<PosHardwareActionResponse> {
  return request<PosHardwareActionResponse>(
    `/inventory/stores/${storeId}/devices/${deviceId}/label/print`,
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
        "X-Reason": reason,
      },
    },
    token,
  );
}

export function listWarehouses(token: string, storeId: number): Promise<Warehouse[]> {
  return requestCollection<Warehouse>(
    `/inventory/stores/${storeId}/warehouses`,
    { method: "GET" },
    token,
  );
}

export function createWarehouse(
  token: string,
  storeId: number,
  payload: Pick<Warehouse, "name" | "code" | "is_default">,
  reason: string,
): Promise<Warehouse> {
  return request<Warehouse>(
    `/inventory/stores/${storeId}/warehouses`,
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token,
  );
}

export function transferBetweenWarehouses(
  token: string,
  payload: WarehouseTransferInput,
  reason: string,
): Promise<{ movement_out: MovementResponse; movement_in: MovementResponse }> {
  return request<{ movement_out: MovementResponse; movement_in: MovementResponse }>(
    "/inventory/warehouses/transfers",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token,
  );
}

export function getProductVariants(
  token: string,
  params: { storeId?: number; deviceId?: number; includeInactive?: boolean } = {},
): Promise<ProductVariant[]> {
  const queryParams = new URLSearchParams();
  if (typeof params.storeId === "number") {
    queryParams.set("store_id", String(params.storeId));
  }
  if (typeof params.deviceId === "number") {
    queryParams.set("device_id", String(params.deviceId));
  }
  if (params.includeInactive) {
    queryParams.set("include_inactive", "true");
  }
  const suffix = queryParams.toString() ? `?${queryParams.toString()}` : "";
  return requestCollection<ProductVariant>(
    `/inventory/variants${suffix}`,
    { method: "GET" },
    token,
  );
}

export function createProductVariant(
  token: string,
  deviceId: number,
  payload: ProductVariantCreateInput,
  reason: string,
): Promise<ProductVariant> {
  return request<ProductVariant>(
    `/inventory/devices/${deviceId}/variants`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Reason": reason },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function updateProductVariant(
  token: string,
  variantId: number,
  payload: ProductVariantUpdateInput,
  reason: string,
): Promise<ProductVariant> {
  return request<ProductVariant>(
    `/inventory/variants/${variantId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "X-Reason": reason },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function archiveProductVariant(
  token: string,
  variantId: number,
  reason: string,
): Promise<ProductVariant> {
  return request<ProductVariant>(
    `/inventory/variants/${variantId}`,
    {
      method: "DELETE",
      headers: { "X-Reason": reason },
    },
    token,
  );
}

export function getProductBundles(
  token: string,
  params: { storeId?: number; includeInactive?: boolean } = {},
): Promise<ProductBundle[]> {
  const queryParams = new URLSearchParams();
  if (typeof params.storeId === "number") {
    queryParams.set("store_id", String(params.storeId));
  }
  if (params.includeInactive) {
    queryParams.set("include_inactive", "true");
  }
  const suffix = queryParams.toString() ? `?${queryParams.toString()}` : "";
  return requestCollection<ProductBundle>(
    `/inventory/bundles${suffix}`,
    { method: "GET" },
    token,
  );
}

export function createProductBundle(
  token: string,
  payload: ProductBundleCreateInput,
  reason: string,
): Promise<ProductBundle> {
  return request<ProductBundle>(
    "/inventory/bundles",
    {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Reason": reason },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function updateProductBundle(
  token: string,
  bundleId: number,
  payload: ProductBundleUpdateInput,
  reason: string,
): Promise<ProductBundle> {
  return request<ProductBundle>(
    `/inventory/bundles/${bundleId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "X-Reason": reason },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function archiveProductBundle(
  token: string,
  bundleId: number,
  reason: string,
): Promise<ProductBundle> {
  return request<ProductBundle>(
    `/inventory/bundles/${bundleId}`,
    {
      method: "DELETE",
      headers: { "X-Reason": reason },
    },
    token,
  );
}

export function getInventoryMetrics(token: string, lowStockThreshold = 5): Promise<InventoryMetrics> {
  return request<InventoryMetrics>(
    `/reports/metrics?low_stock_threshold=${lowStockThreshold}`,
    { method: "GET" },
    token
  );
}

export function getInventoryAlerts(
  token: string,
  params: { storeId?: number; threshold?: number } = {},
): Promise<InventoryAlertsResponse> {
  const searchParams = new URLSearchParams();
  if (params.storeId) {
    searchParams.set("store_id", String(params.storeId));
  }
  if (typeof params.threshold === "number") {
    searchParams.set("threshold", String(params.threshold));
  }
  const query = searchParams.toString();
  const suffix = query ? `?${query}` : "";
  return request<InventoryAlertsResponse>(
    `/reports/alerts${suffix}`,
    { method: "GET" },
    token,
  );
}

export function registerInventoryReceiving(
  token: string,
  payload: InventoryReceivingRequest,
  reason: string,
): Promise<InventoryReceivingResult> {
  return request<InventoryReceivingResult>(
    "/inventory/counts/receipts",
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token,
  );
}

export function registerInventoryCycleCount(
  token: string,
  payload: InventoryCycleCountRequest,
  reason: string,
): Promise<InventoryCycleCountResult> {
  return request<InventoryCycleCountResult>(
    "/inventory/counts/cycle",
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token,
  );
}

export function registerMovement(
  token: string,
  storeId: number,
  payload: MovementInput,
  comment: string
) {
  return request(`/inventory/stores/${storeId}/movements`, {
    method: "POST",
    body: JSON.stringify(payload),
    headers: { "X-Reason": comment },
  }, token);
}

export function getMinimumStockAlerts(
  token: string,
  params: { storeId?: number } = {},
): Promise<MinimumStockAlertsResponse> {
  const searchParams = new URLSearchParams();
  if (params.storeId) {
    searchParams.set("store_id", String(params.storeId));
  }
  const query = searchParams.toString();
  const suffix = query ? `?${query}` : "";
  return request<MinimumStockAlertsResponse>(`/alerts/inventory/minimum${suffix}`, { method: "GET" }, token);
}
export type { Store } from "./types";
