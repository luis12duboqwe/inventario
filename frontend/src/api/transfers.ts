import { request, requestCollection } from "./client";

export type TransferOrderItem = {
  id: number;
  transfer_order_id: number;
  device_id: number;
  quantity: number;
  reservation_id?: number | null;
  device_name?: string | null;
  sku?: string | null;
  dispatched_quantity?: number;
  received_quantity?: number;
};

export type TransferOrder = {
  id: number;
  origin_store_id: number;
  destination_store_id: number;
  status: "SOLICITADA" | "EN_TRANSITO" | "RECIBIDA" | "CANCELADA";
  reason?: string | null;
  created_at: string;
  updated_at: string;
  dispatched_at?: string | null;
  received_at?: string | null;
  cancelled_at?: string | null;
  items: TransferOrderItem[];
  origin_store_name?: string | null;
  destination_store_name?: string | null;
  ultima_accion?: {
    usuario?: string | null;
    timestamp: string;
  } | null;
};

export type TransferOrderInput = {
  origin_store_id: number;
  destination_store_id: number;
  reason?: string;
  items: { device_id: number; quantity: number; reservation_id?: number | null }[];
};

export type TransferReceptionItem = {
  item_id: number;
  received_quantity: number;
};

export type TransferTransitionInput = {
  reason?: string;
  items?: TransferReceptionItem[];
};

export type TransferReportDevice = {
  sku?: string | null;
  name?: string | null;
  quantity: number;
};

export type TransferReportItem = {
  id: number;
  folio: string;
  origin_store: string;
  destination_store: string;
  status: TransferOrder["status"];
  reason?: string | null;
  requested_at: string;
  dispatched_at?: string | null;
  received_at?: string | null;
  cancelled_at?: string | null;
  requested_by?: string | null;
  dispatched_by?: string | null;
  received_by?: string | null;
  cancelled_by?: string | null;
  total_quantity: number;
  devices: TransferReportDevice[];
};

export type TransferReportTotals = {
  total_transfers: number;
  pending: number;
  in_transit: number;
  completed: number;
  cancelled: number;
  total_quantity: number;
};

export type TransferReportFilters = {
  store_id?: number;
  origin_store_id?: number;
  destination_store_id?: number;
  status?: TransferOrder["status"];
  date_from?: string;
  date_to?: string;
};

export type TransferReport = {
  generated_at: string;
  filters: TransferReportFilters;
  totals: TransferReportTotals;
  items: TransferReportItem[];
};

export function listTransfers(token: string, storeId?: number): Promise<TransferOrder[]> {
  const params = new URLSearchParams();
  params.set("limit", "25");
  if (typeof storeId === "number") {
    params.set("store_id", String(storeId));
  }
  const query = params.toString();
  const path = `/transfers${query ? `?${query}` : ""}`;
  return requestCollection<TransferOrder>(path, { method: "GET" }, token);
}

export function getTransfer(token: string, transferId: number): Promise<TransferOrder> {
  return request<TransferOrder>(`/transfers/${transferId}`, { method: "GET" }, token);
}

export function createTransferOrder(
  token: string,
  payload: TransferOrderInput,
  reason: string
): Promise<TransferOrder> {
  return request(
    "/transfers",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function dispatchTransferOrder(
  token: string,
  transferId: number,
  payload: TransferTransitionInput,
  reason: string
): Promise<TransferOrder> {
  return request(
    `/transfers/${transferId}/dispatch`,
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function receiveTransferOrder(
  token: string,
  transferId: number,
  payload: TransferTransitionInput,
  reason: string
): Promise<TransferOrder> {
  return request(
    `/transfers/${transferId}/receive`,
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function cancelTransferOrder(
  token: string,
  transferId: number,
  payload: TransferTransitionInput,
  reason: string
): Promise<TransferOrder> {
  return request(
    `/transfers/${transferId}/cancel`,
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

function buildTransferReportQuery(filters: TransferReportFilters = {}): string {
  const params = new URLSearchParams();
  if (typeof filters.store_id === "number") {
    params.set("store_id", String(filters.store_id));
  }
  if (typeof filters.origin_store_id === "number") {
    params.set("origin_store_id", String(filters.origin_store_id));
  }
  if (typeof filters.destination_store_id === "number") {
    params.set("destination_store_id", String(filters.destination_store_id));
  }
  if (filters.status) {
    params.set("status", filters.status);
  }
  if (filters.date_from) {
    params.set("date_from", filters.date_from);
  }
  if (filters.date_to) {
    params.set("date_to", filters.date_to);
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function getTransferReport(
  token: string,
  filters: TransferReportFilters = {},
): Promise<TransferReport> {
  const query = buildTransferReportQuery(filters);
  return request<TransferReport>(`/transfers/report${query}`, { method: "GET" }, token);
}

export function exportTransferReportPdf(
  token: string,
  reason: string,
  filters: TransferReportFilters = {},
): Promise<Blob> {
  const query = buildTransferReportQuery(filters);
  return request<Blob>(
    `/transfers/export/pdf${query}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
}

export function exportTransferReportExcel(
  token: string,
  reason: string,
  filters: TransferReportFilters = {},
): Promise<Blob> {
  const query = buildTransferReportQuery(filters);
  return request<Blob>(
    `/transfers/export/xlsx${query}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
}
