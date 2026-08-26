import { request } from "./client";
import type {
  RepairOrder,
  RepairOrderClosePayload,
  RepairOrderCreatePayload,
  RepairOrderListParams,
  RepairOrderPartCreatePayload,
  RepairOrderPartsPayload,
  RepairOrderUpdatePayload,
} from "../types/repairs";

export type RepairMetrics = {
  total_orders: number;
  open_orders: number;
  closed_orders: number;
  average_resolution_hours: number;
};

function buildRepairQuery(params: RepairOrderListParams = {}): string {
  const searchParams = new URLSearchParams();
  if (params.storeId != null) searchParams.set("store_id", String(params.storeId));
  if (params.customerId != null) searchParams.set("customer_id", String(params.customerId));
  if (params.status) searchParams.set("status", params.status);
  if (params.search) searchParams.set("q", params.search);
  if (params.limit != null) searchParams.set("limit", String(params.limit));
  if (params.offset != null) searchParams.set("offset", String(params.offset));
  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

export function listRepairOrders(
  token: string,
  params: RepairOrderListParams = {}
): Promise<RepairOrder[]> {
  return request<RepairOrder[]>(`/repairs${buildRepairQuery(params)}`, {}, token);
}

export function getRepairOrder(token: string, repairId: number): Promise<RepairOrder> {
  return request<RepairOrder>(`/repairs/${repairId}`, {}, token);
}

export function createRepairOrder(
  token: string,
  payload: RepairOrderCreatePayload,
  reason: string
): Promise<RepairOrder> {
  return request<RepairOrder>(
    "/repairs",
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function updateRepairOrder(
  token: string,
  repairId: number,
  payload: RepairOrderUpdatePayload,
  reason: string
): Promise<RepairOrder> {
  return request<RepairOrder>(
    `/repairs/${repairId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function addRepairOrderPart(
  token: string,
  repairId: number,
  payload: RepairOrderPartCreatePayload,
  reason: string
): Promise<RepairOrder> {
  return request<RepairOrder>(
    `/repairs/${repairId}/parts`,
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function replaceRepairOrderParts(
  token: string,
  repairId: number,
  payload: RepairOrderPartsPayload,
  reason: string
): Promise<RepairOrder> {
  return request<RepairOrder>(
    `/repairs/${repairId}/parts`,
    { method: "PUT", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function removeRepairOrderPart(
  token: string,
  repairId: number,
  partId: number,
  reason: string
): Promise<RepairOrder> {
  return request<RepairOrder>(
    `/repairs/${repairId}/parts/${partId}`,
    { method: "DELETE", headers: { "X-Reason": reason } },
    token
  );
}

export function deleteRepairOrder(token: string, repairId: number, reason: string): Promise<void> {
  return request<void>(
    `/repairs/${repairId}`,
    { method: "DELETE", headers: { "X-Reason": reason } },
    token
  );
}

export function closeRepairOrder(
  token: string,
  repairId: number,
  payload: RepairOrderClosePayload | undefined,
  reason: string
): Promise<Blob> {
  const init: RequestInit & { responseType: "blob" } = payload
    ? {
        method: "POST",
        body: JSON.stringify(payload),
        headers: { "X-Reason": reason },
        responseType: "blob",
      }
    : {
        method: "POST",
        headers: { "X-Reason": reason },
        responseType: "blob",
      };

  return request<Blob>(`/repairs/${repairId}/close`, init, token);
}

export async function downloadRepairOrderPdf(token: string, repairId: number): Promise<Blob> {
  return request<Blob>(`/repairs/${repairId}/pdf`, { method: "GET", responseType: "blob" }, token);
}
