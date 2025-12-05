import { request } from "../client";
import {
  InventoryReceivingRequest,
  InventoryReceivingResult,
  InventoryCycleCountRequest,
  InventoryCycleCountResult
} from "../inventoryTypes";

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
