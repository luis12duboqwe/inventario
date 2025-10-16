import {
  downloadInventoryCsv,
  downloadInventoryPdf,
  getDevices,
  getSupplierBatchOverview,
  registerMovement,
} from "../../../api";
import type { MovementInput, SupplierBatchOverviewItem } from "../../../api";

export const inventoryService = {
  fetchDevices: getDevices,
  registerMovement: (
    token: string,
    storeId: number,
    payload: MovementInput,
    reason: string,
  ) => registerMovement(token, storeId, payload, reason),
  downloadInventoryReport: (token: string, reason: string) =>
    downloadInventoryPdf(token, reason),
  downloadInventoryCsv: (token: string, reason: string) =>
    downloadInventoryCsv(token, reason),
  fetchSupplierBatchOverview: (
    token: string,
    storeId: number,
    limit = 5,
  ): Promise<SupplierBatchOverviewItem[]> =>
    getSupplierBatchOverview(token, storeId, limit),
};
