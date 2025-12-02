import { request, requestCollection } from "./client";

export type RecurringOrderType = "purchase" | "transfer";

export type RecurringOrder = {
  id: number;
  name: string;
  description?: string | null;
  order_type: RecurringOrderType;
  store_id?: number | null;
  store_name?: string | null;
  payload: Record<string, unknown>;
  created_by_id?: number | null;
  created_by_name?: string | null;
  last_used_by_id?: number | null;
  last_used_by_name?: string | null;
  created_at: string;
  updated_at: string;
  last_used_at?: string | null;
};

export type RecurringOrderPayload = {
  name: string;
  description?: string | null;
  order_type: RecurringOrderType;
  payload: Record<string, unknown>;
};

export type RecurringOrderExecutionResult = {
  template_id: number;
  order_type: RecurringOrderType;
  reference_id: number;
  store_id?: number | null;
  created_at: string;
  summary: string;
};

export type OperationsHistoryRecord = {
  id: string;
  operation_type: "purchase" | "transfer_dispatch" | "transfer_receive" | "sale";
  occurred_at: string;
  store_id?: number | null;
  store_name?: string | null;
  technician_id?: number | null;
  technician_name?: string | null;
  reference?: string | null;
  description: string;
  amount?: number | null;
};

export type OperationsTechnicianSummary = {
  id: number;
  name: string;
};

export type OperationsHistoryResponse = {
  records: OperationsHistoryRecord[];
  technicians: OperationsTechnicianSummary[];
};

export type OperationsHistoryFilters = {
  storeId?: number | null;
  technicianId?: number | null;
  startDate?: string;
  endDate?: string;
};

export function listRecurringOrders(
  token: string,
  orderType?: RecurringOrderType
): Promise<RecurringOrder[]> {
  const params = new URLSearchParams();
  if (orderType) {
    params.set("order_type", orderType);
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return requestCollection<RecurringOrder>(
    `/operations/recurring-orders${suffix}`,
    { method: "GET" },
    token,
  );
}

export function createRecurringOrder(
  token: string,
  payload: RecurringOrderPayload,
  reason: string
): Promise<RecurringOrder> {
  return request<RecurringOrder>(
    "/operations/recurring-orders",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function executeRecurringOrder(
  token: string,
  templateId: number,
  reason: string
): Promise<RecurringOrderExecutionResult> {
  return request<RecurringOrderExecutionResult>(
    `/operations/recurring-orders/${templateId}/execute`,
    { method: "POST", headers: { "X-Reason": reason } },
    token
  );
}

export function listOperationsHistory(
  token: string,
  filters: OperationsHistoryFilters = {}
): Promise<OperationsHistoryResponse> {
  const params = new URLSearchParams();
  if (filters.storeId != null) {
    params.set("store_id", String(filters.storeId));
  }
  if (filters.technicianId != null) {
    params.set("technician_id", String(filters.technicianId));
  }
  if (filters.startDate) {
    params.set("start_date", filters.startDate);
  }
  if (filters.endDate) {
    params.set("end_date", filters.endDate);
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<OperationsHistoryResponse>(`/operations/history${suffix}`, { method: "GET" }, token);
}
