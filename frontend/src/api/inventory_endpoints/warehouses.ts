import { request, requestCollection } from "../client";
import {
  Warehouse,
  WarehouseTransferInput,
  MovementResponse
} from "../inventoryTypes";

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
