import { downloadInventoryPdf, getDevices, registerMovement } from "../../../api";
import type { MovementInput } from "../../../api";

export const inventoryService = {
  fetchDevices: getDevices,
  registerMovement: (
    token: string,
    storeId: number,
    payload: MovementInput,
    reason: string,
  ) => registerMovement(token, storeId, payload, reason),
  downloadInventoryReport: (token: string, reason: string) => downloadInventoryPdf(token, reason),
  downloadInventoryReport: (token: string) => downloadInventoryPdf(token),
};
