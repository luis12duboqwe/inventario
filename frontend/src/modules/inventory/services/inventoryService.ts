import {
  downloadInventoryCsv,
  downloadInventoryPdf,
  exportStoreDevicesCsv,
  getDevices,
  getSupplierBatchOverview,
  importStoreDevicesCsv,
  registerMovement,
} from "../../../api";
import type { DeviceImportSummary, MovementInput, SupplierBatchOverviewItem } from "../../../api";

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
};
