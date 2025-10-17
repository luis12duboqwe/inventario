import {
  downloadInventoryCsv,
  downloadInventoryMovementsCsv,
  downloadInventoryPdf,
  downloadInventoryValueCsv,
  downloadTopProductsCsv,
  exportStoreDevicesCsv,
  getDevices,
  getInventoryCurrentReport,
  getInventoryMovementsReport,
  getInventoryValueReport,
  getSupplierBatchOverview,
  getTopProductsReport,
  importStoreDevicesCsv,
  registerMovement,
} from "../../../api";
import type {
  DeviceImportSummary,
  InventoryCurrentFilters,
  InventoryCurrentReport,
  InventoryMovementsFilters,
  InventoryMovementsReport,
  InventoryTopProductsFilters,
  InventoryValueFilters,
  InventoryValueReport,
  MovementInput,
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
  downloadInventoryValueCsv: (
    token: string,
    reason: string,
    filters: InventoryValueFilters = {},
  ) => downloadInventoryValueCsv(token, reason, filters),
  downloadInventoryMovementsCsv: (
    token: string,
    reason: string,
    filters: InventoryMovementsFilters = {},
  ) => downloadInventoryMovementsCsv(token, reason, filters),
  downloadTopProductsCsv: (
    token: string,
    reason: string,
    filters: InventoryTopProductsFilters = {},
  ) => downloadTopProductsCsv(token, reason, filters),
};
