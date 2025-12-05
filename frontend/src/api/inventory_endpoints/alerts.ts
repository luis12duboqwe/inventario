import { request } from "../client";
import {
  InventoryMetrics,
  InventoryAlertsResponse,
  MinimumStockAlertsResponse
} from "../inventoryTypes";

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
