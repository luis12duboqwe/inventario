import {
  downloadInventoryCsv,
  downloadInventoryCurrentCsv,
  downloadInventoryCurrentPdf,
  downloadInventoryCurrentXlsx,
  downloadInventoryMovementsCsv,
  downloadInventoryMovementsPdf,
  downloadInventoryMovementsXlsx,
  downloadInventoryPdf,
  downloadInventoryValueCsv,
  downloadInventoryValuePdf,
  downloadInventoryValueXlsx,
  downloadTopProductsCsv,
  downloadTopProductsPdf,
  downloadTopProductsXlsx,
  exportStoreDevicesCsv,
  getDevices,
  getIncompleteDevices,
  getInventoryReservations,
  getInventoryCurrentReport,
  getInventoryMovementsReport,
  getInventoryValueReport,
  getSupplierBatchOverview,
  getTopProductsReport,
  importStoreDevicesCsv,
  createInventoryReservation,
  renewInventoryReservation,
  cancelInventoryReservation,
  registerMovement,
  smartInventoryImport,
  getSmartImportHistory,
} from "../../../api";
import type {
  DeviceImportSummary,
  InventoryCurrentFilters,
  InventoryImportHistoryEntry,
  InventoryCurrentReport,
  InventoryMovementsFilters,
  InventoryMovementsReport,
  InventorySmartImportResponse,
  InventoryTopProductsFilters,
  InventoryValueFilters,
  InventoryValueReport,
  InventoryReservation,
  InventoryReservationInput,
  InventoryReservationRenewInput,
  MovementInput,
  PaginatedResponse,
  SupplierBatchOverviewItem,
  TopProductsReport,
} from "../../../api";

export const inventoryService = {
  fetchDevices: getDevices,
  registerMovement: (
    token: string,
    storeId: number,
    payload: MovementInput,
    comment: string,
  ) => registerMovement(token, storeId, payload, comment),
  downloadInventoryReport: (token: string, reason: string) =>
    downloadInventoryPdf(token, reason),
  downloadInventoryCsv: (token: string, reason: string) =>
    downloadInventoryCsv(token, reason),
  exportCatalogCsv: (
    token: string,
    storeId: number,
    filters: Parameters<typeof getDevices>[2],
    reason: string,
  ) => exportStoreDevicesCsv(token, storeId, filters, reason),
  importCatalogCsv: (
    token: string,
    storeId: number,
    file: File,
    reason: string,
  ): Promise<DeviceImportSummary> => importStoreDevicesCsv(token, storeId, file, reason),
  smartImportInventory: (
    token: string,
    file: File,
    reason: string,
    options: Parameters<typeof smartInventoryImport>[3] = {},
  ): Promise<InventorySmartImportResponse> =>
    smartInventoryImport(token, file, reason, options),
  fetchSmartImportHistory: (
    token: string,
    limit = 10,
  ): Promise<InventoryImportHistoryEntry[]> => getSmartImportHistory(token, limit),
  fetchIncompleteDevices: (
    token: string,
    storeId?: number,
    limit = 100,
  ) => getIncompleteDevices(token, storeId, limit),
  fetchReservations: (
    token: string,
    params: Parameters<typeof getInventoryReservations>[1],
  ): Promise<PaginatedResponse<InventoryReservation>> =>
    getInventoryReservations(token, params),
  createReservation: (
    token: string,
    payload: InventoryReservationInput,
    reason: string,
  ): Promise<InventoryReservation> =>
    createInventoryReservation(token, payload, reason),
  renewReservation: (
    token: string,
    reservationId: number,
    payload: InventoryReservationRenewInput,
    reason: string,
  ): Promise<InventoryReservation> =>
    renewInventoryReservation(token, reservationId, payload, reason),
  cancelReservation: (
    token: string,
    reservationId: number,
    reason: string,
  ): Promise<InventoryReservation> =>
    cancelInventoryReservation(token, reservationId, reason),
  fetchSupplierBatchOverview: (
    token: string,
    storeId: number,
    limit = 5,
  ): Promise<SupplierBatchOverviewItem[]> =>
    getSupplierBatchOverview(token, storeId, limit),
  fetchInventoryCurrentReport: (
    token: string,
    filters: InventoryCurrentFilters = {},
  ): Promise<InventoryCurrentReport> => getInventoryCurrentReport(token, filters),
  fetchInventoryValueReport: (
    token: string,
    filters: InventoryValueFilters = {},
  ): Promise<InventoryValueReport> => getInventoryValueReport(token, filters),
  fetchInventoryMovementsReport: (
    token: string,
    filters: InventoryMovementsFilters = {},
  ): Promise<InventoryMovementsReport> => getInventoryMovementsReport(token, filters),
  fetchTopProductsReport: (
    token: string,
    filters: InventoryTopProductsFilters = {},
  ): Promise<TopProductsReport> => getTopProductsReport(token, filters),
  downloadInventoryCurrentCsv: (
    token: string,
    reason: string,
    filters: InventoryCurrentFilters = {},
  ) => downloadInventoryCurrentCsv(token, reason, filters),
  downloadInventoryCurrentPdf: (
    token: string,
    reason: string,
    filters: InventoryCurrentFilters = {},
  ) => downloadInventoryCurrentPdf(token, reason, filters),
  downloadInventoryCurrentXlsx: (
    token: string,
    reason: string,
    filters: InventoryCurrentFilters = {},
  ) => downloadInventoryCurrentXlsx(token, reason, filters),
  downloadInventoryValueCsv: (
    token: string,
    reason: string,
    filters: InventoryValueFilters = {},
  ) => downloadInventoryValueCsv(token, reason, filters),
  downloadInventoryValuePdf: (
    token: string,
    reason: string,
    filters: InventoryValueFilters = {},
  ) => downloadInventoryValuePdf(token, reason, filters),
  downloadInventoryValueXlsx: (
    token: string,
    reason: string,
    filters: InventoryValueFilters = {},
  ) => downloadInventoryValueXlsx(token, reason, filters),
  downloadInventoryMovementsCsv: (
    token: string,
    reason: string,
    filters: InventoryMovementsFilters = {},
  ) => downloadInventoryMovementsCsv(token, reason, filters),
  downloadInventoryMovementsPdf: (
    token: string,
    reason: string,
    filters: InventoryMovementsFilters = {},
  ) => downloadInventoryMovementsPdf(token, reason, filters),
  downloadInventoryMovementsXlsx: (
    token: string,
    reason: string,
    filters: InventoryMovementsFilters = {},
  ) => downloadInventoryMovementsXlsx(token, reason, filters),
  downloadTopProductsCsv: (
    token: string,
    reason: string,
    filters: InventoryTopProductsFilters = {},
  ) => downloadTopProductsCsv(token, reason, filters),
  downloadTopProductsPdf: (
    token: string,
    reason: string,
    filters: InventoryTopProductsFilters = {},
  ) => downloadTopProductsPdf(token, reason, filters),
  downloadTopProductsXlsx: (
    token: string,
    reason: string,
    filters: InventoryTopProductsFilters = {},
  ) => downloadTopProductsXlsx(token, reason, filters),
};
