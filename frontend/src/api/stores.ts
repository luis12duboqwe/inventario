import { request, requestCollection } from "./client";
import { Device } from "./inventory";
import { Store } from "./types";
export type { Store };

export type StoreCreateInput = {
  name: string;
  code?: string | undefined;
  address?: string | undefined;
  is_active?: boolean;
  timezone?: string | undefined;
};

export type StoreUpdateInput = {
  name?: string | undefined;
  code?: string | undefined;
  address?: string | undefined;
  is_active?: boolean | undefined;
  timezone?: string | undefined;
};

export type Summary = {
  store_id: number;
  store_name: string;
  total_items: number;
  total_value: number;
  devices: Device[];
};

export function getStores(token: string): Promise<Store[]> {
  // Evita depender del slash final que algunos proxies tratan distinto.
  return requestCollection<Store>("/stores?limit=200", { method: "GET" }, token);
}

export function createStore(
  token: string,
  payload: StoreCreateInput,
  reason: string,
): Promise<Store> {
  const safeReason = (reason ?? "").trim();
  return request<Store>(
    "/stores",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": safeReason } },
    token,
  );
}

export function updateStore(
  token: string,
  storeId: number,
  payload: StoreUpdateInput,
  reason: string,
): Promise<Store> {
  const safeReason = (reason ?? "").trim();
  return request<Store>(
    `/stores/${storeId}`,
    { method: "PUT", body: JSON.stringify(payload), headers: { "X-Reason": safeReason } },
    token,
  );
}

export function getSummary(token: string): Promise<Summary[]> {
  return requestCollection<Summary>("/inventory/summary", { method: "GET" }, token);
}
