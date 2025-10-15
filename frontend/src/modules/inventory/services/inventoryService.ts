import { downloadInventoryPdf, getDevices, registerMovement } from "../../../api";
import type { MovementInput } from "../../../api";

export const inventoryService = {
  fetchDevices: getDevices,
  registerMovement: (token: string, payload: MovementInput) => registerMovement(token, payload),
  downloadInventoryReport: (token: string) => downloadInventoryPdf(token),
};
