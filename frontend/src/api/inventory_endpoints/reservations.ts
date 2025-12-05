import { request } from "../client";
import { PaginatedResponse } from "../types";
import {
  InventoryReservation,
  InventoryReservationState,
  InventoryReservationInput,
  InventoryReservationRenewInput
} from "../inventoryTypes";

export function getInventoryReservations(
  token: string,
  params: {
    storeId?: number;
    deviceId?: number;
    status?: InventoryReservationState;
    includeExpired?: boolean;
    page?: number;
    size?: number;
    limit?: number;
    offset?: number;
  } = {},
): Promise<PaginatedResponse<InventoryReservation>> {
  const queryParams = new URLSearchParams();
  if (typeof params.storeId === "number") {
    queryParams.set("store_id", String(params.storeId));
  }
  if (typeof params.deviceId === "number") {
    queryParams.set("device_id", String(params.deviceId));
  }
  if (params.status) {
    queryParams.set("status_filter", params.status);
  }
  if (params.includeExpired) {
    queryParams.set("include_expired", "true");
  }
  if (typeof params.page === "number") {
    queryParams.set("page", String(params.page));
  }
  if (typeof params.size === "number") {
    queryParams.set("size", String(params.size));
  }
  if (typeof params.limit === "number") {
    queryParams.set("limit", String(params.limit));
  }
  if (typeof params.offset === "number") {
    queryParams.set("offset", String(params.offset));
  }
  const suffix = queryParams.toString() ? `?${queryParams.toString()}` : "";
  return request<PaginatedResponse<InventoryReservation>>(
    `/inventory/reservations${suffix}`,
    { method: "GET" },
    token,
  );
}

export function createInventoryReservation(
  token: string,
  payload: InventoryReservationInput,
  reason: string,
): Promise<InventoryReservation> {
  return request<InventoryReservation>(
    "/inventory/reservations",
    {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Reason": reason },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function renewInventoryReservation(
  token: string,
  reservationId: number,
  payload: InventoryReservationRenewInput,
  reason: string,
): Promise<InventoryReservation> {
  return request<InventoryReservation>(
    `/inventory/reservations/${reservationId}/renew`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json", "X-Reason": reason },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function cancelInventoryReservation(
  token: string,
  reservationId: number,
  reason: string,
): Promise<InventoryReservation> {
  return request<InventoryReservation>(
    `/inventory/reservations/${reservationId}/cancel`,
    {
      method: "POST",
      headers: { "X-Reason": reason },
    },
    token,
  );
}
