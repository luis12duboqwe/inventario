import { request, requestCollection } from "./client";
import type { Customer } from "./customers";
import type { Device } from "./inventory";
import type { Store } from "./stores";

export type RepairStatus =
  | "PENDIENTE"
  | "EN_PROCESO"
  | "LISTO"
  | "ENTREGADO"
  | "CANCELADO";

export type RepairPartSource = "STOCK" | "EXTERNAL";

export type RepairOrder = {
  id: number;
  store_id: number;
  store?: Store;
  customer_id: number | null;
  customer?: Customer;
  customer_name?: string | null;
  customer_contact?: string | null;
  device_id?: number | null;
  device?: Device;
  device_description: string;
  device_model?: string | null;
  imei?: string | null;
  problem_description: string;
  damage_type: string;
  diagnosis?: string | null;
  status: RepairStatus;
  technician_id?: number | null;
  technician_name: string;
  estimated_cost: number;
  labor_cost: number;
  parts_cost: number;
  total_cost: number;
  final_cost?: number | null;
  deposit_amount: number;
  inventory_adjusted: boolean;
  created_at: string;
  opened_at: string;
  updated_at: string;
  completed_at?: string | null;
  delivered_at?: string | null;
  notes?: string | null;
  parts: RepairOrderPart[];
};

export type RepairOrderPart = {
  id: number;
  repair_order_id: number;
  device_id?: number | null;
  device?: Device;
  part_name?: string | null;
  quantity: number;
  unit_cost: number;
  unit_price?: number;
  source: RepairPartSource;
  created_at: string;
};

export type RepairOrderPayload = {
  store_id: number;
  customer_id: number | null;
  customer_name?: string | null;
  customer_contact?: string | null;
  device_id?: number | null;
  device_model?: string | null;
  imei?: string | null;
  device_description: string;
  problem_description: string;
  diagnosis?: string | null;
  estimated_cost: number;
  labor_cost?: number;
  deposit_amount: number;
  technician_id?: number | null;
  technician_name: string;
  damage_type: string;
  notes?: string | null;
  parts: Array<{
    source: RepairPartSource;
    quantity: number;
    unit_cost: number;
    device_id?: number;
    part_name?: string;
  }>;
};

export type RepairOrderUpdatePayload = Partial<RepairOrderPayload> & {
  status?: RepairStatus;
};

export type RepairOrderPartsPayload = {
  parts: Array<{
    source: RepairPartSource;
    quantity: number;
    unit_cost: number;
    device_id?: number;
    part_name?: string;
  }>;
};

export type RepairOrderClosePayload = {
  final_cost: number;
  notes?: string | null;
};

export function listRepairOrders(
  token: string,
  params: {
    store_id?: number;
    branchId?: number;
    status?: string;
    q?: string;
    from?: string;
    to?: string;
    limit?: number;
    offset?: number;
  }
): Promise<RepairOrder[]> {
  const searchParams = new URLSearchParams();
  if (params.store_id) {
    searchParams.append("store_id", String(params.store_id));
  }
  if (params.branchId) {
    searchParams.append("branchId", String(params.branchId));
  }
  if (params.status) {
    searchParams.append("status", params.status);
  }
  if (params.q) {
    searchParams.append("q", params.q);
  }
  if (params.from) {
    searchParams.append("from", params.from);
  }
  if (params.to) {
    searchParams.append("to", params.to);
  }
  if (params.limit) {
    searchParams.append("limit", String(params.limit));
  }
  if (typeof params.offset === "number") {
    searchParams.append("offset", String(params.offset));
  }
  const query = searchParams.toString();
  const suffix = query ? `?${query}` : "";
  return requestCollection<RepairOrder>(`/repairs${suffix}`, { method: "GET" }, token);
}

export function createRepairOrder(
  token: string,
  payload: RepairOrderPayload,
  reason: string
): Promise<RepairOrder> {
  return request<RepairOrder>(
    "/repairs",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
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
    { method: "PUT", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function appendRepairOrderParts(
  token: string,
  repairId: number,
  payload: RepairOrderPartsPayload,
  reason: string
): Promise<RepairOrder> {
  return request<RepairOrder>(
    `/repairs/${repairId}/parts`,
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
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
  const init: RequestInit = payload
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
