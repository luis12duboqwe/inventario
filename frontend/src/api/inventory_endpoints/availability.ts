import { request } from "../client";
import {
  InventoryAvailabilityParams,
  InventoryAvailabilityResponse
} from "../inventoryTypes";

export function getInventoryAvailability(
  token: string,
  params: InventoryAvailabilityParams = {},
): Promise<InventoryAvailabilityResponse> {
  const queryParams = new URLSearchParams();
  if (params.query) {
    queryParams.set("query", params.query);
  }
  if (params.skus && params.skus.length > 0) {
    queryParams.set("skus", params.skus.join(","));
  }
  if (params.deviceIds && params.deviceIds.length > 0) {
    queryParams.set("device_ids", params.deviceIds.join(","));
  }
  if (params.limit) {
    queryParams.set("limit", String(params.limit));
  }
  const suffix = queryParams.toString() ? `?${queryParams.toString()}` : "";
  return request<InventoryAvailabilityResponse>(
    `/inventory/availability${suffix}`,
    { method: "GET" },
    token,
  );
}
