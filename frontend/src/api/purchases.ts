import { request, requestCollection } from "./client";
import { ReturnDisposition, ReturnReasonCategory } from "./types";

export type PurchaseOrderStatus =
  | "BORRADOR"
  | "PENDIENTE"
  | "APROBADA"
  | "ENVIADA"
  | "PARCIAL"
  | "COMPLETADA"
  | "CANCELADA";

export type PurchaseOrderDocument = {
  id: number;
  purchase_order_id: number;
  filename: string;
  content_type: string;
  storage_backend: string;
  uploaded_at: string;
  uploaded_by_id: number | null;
  download_url?: string | null;
};

export type PurchaseOrderStatusEvent = {
  id: number;
  purchase_order_id: number;
  status: PurchaseOrderStatus;
  note?: string | null;
  created_at: string;
  created_by_id: number | null;
  created_by_name?: string | null;
};

export type PurchaseOrderItem = {
  id: number;
  purchase_order_id: number;
  device_id: number;
  quantity_ordered: number;
  quantity_received: number;
  unit_cost: number;
};

export type PurchaseReturn = {
  id: number;
  purchase_order_id: number;
  device_id: number;
  quantity: number;
  reason: string;
  reason_category: ReturnReasonCategory;
  disposition: ReturnDisposition;
  warehouse_id?: number | null;
  supplier_ledger_entry_id?: number | null;
  corporate_reason?: string | null;
  credit_note_amount: number;
  processed_by_id: number | null;
  approved_by_id?: number | null;
  approved_by_name?: string | null;
  receipt_pdf_base64?: string | null;
  receipt_url?: string | null;
  created_at: string;
};

export type PurchaseOrder = {
  id: number;
  store_id: number;
  supplier: string;
  status: PurchaseOrderStatus;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  created_by_id?: number | null;
  closed_at?: string | null;
  items: PurchaseOrderItem[];
  returns: PurchaseReturn[];
  documents: PurchaseOrderDocument[];
  status_history: PurchaseOrderStatusEvent[];
};

export type PurchaseOrderStatusUpdateInput = {
  status: PurchaseOrderStatus;
  note?: string | null;
};

export type PurchaseOrderEmailInput = {
  recipients: string[];
  message?: string | null;
  include_documents?: boolean;
};

export type PurchaseOrderCreateInput = {
  store_id: number;
  supplier: string;
  items: { device_id: number; quantity_ordered: number; unit_cost: number }[];
  notes?: string;
};

export type PurchaseReceiveInput = {
  items: { device_id: number; quantity: number; batch_code?: string | null }[];
};

export type PurchaseReturnInput = {
  device_id: number;
  quantity: number;
  reason: string;
  disposition?: ReturnDisposition;
  warehouse_id?: number | null;
  category?: ReturnReasonCategory;
};

export type PurchaseImportResponse = {
  imported: number;
  orders: PurchaseOrder[];
  errors: string[];
};

export type PurchaseSuggestionItem = {
  store_id: number;
  store_name: string;
  supplier_id: number | null;
  supplier_name: string | null;
  device_id: number;
  sku: string;
  name: string;
  current_quantity: number;
  minimum_stock: number;
  suggested_quantity: number;
  average_daily_sales: number;
  projected_coverage_days: number | null;
  last_30_days_sales: number;
  unit_cost: number;
  reason: "below_minimum" | "projected_consumption";
  suggested_value: number;
};

export type PurchaseSuggestionStore = {
  store_id: number;
  store_name: string;
  total_suggested: number;
  total_value: number;
  items: PurchaseSuggestionItem[];
};

export type PurchaseSuggestionsResponse = {
  generated_at: string;
  lookback_days: number;
  planning_horizon_days: number;
  minimum_stock: number;
  total_items: number;
  stores: PurchaseSuggestionStore[];
};

export type PurchaseVendor = {
  id_proveedor: number;
  nombre: string;
  telefono?: string | null;
  correo?: string | null;
  direccion?: string | null;
  tipo?: string | null;
  notas?: string | null;
  estado: string;
  total_compras: number;
  total_impuesto: number;
  compras_registradas: number;
  ultima_compra?: string | null;
};

export type PurchaseVendorPayload = {
  nombre: string;
  telefono?: string;
  correo?: string;
  direccion?: string;
  tipo?: string;
  notas?: string;
  estado?: string;
};

export type PurchaseVendorStatusPayload = {
  estado: string;
};

export type PurchaseRecordItem = {
  id_detalle: number;
  producto_id: number;
  cantidad: number;
  costo_unitario: number;
  subtotal: number;
  producto_nombre?: string | null;
};

export type PurchaseRecord = {
  id_compra: number;
  proveedor_id: number;
  proveedor_nombre: string;
  usuario_id: number;
  usuario_nombre?: string | null;
  fecha: string;
  forma_pago: string;
  estado: string;
  subtotal: number;
  impuesto: number;
  total: number;
  items: PurchaseRecordItem[];
};

export type PurchaseRecordItemPayload = {
  producto_id: number;
  cantidad: number;
  costo_unitario: number;
};

export type PurchaseRecordPayload = {
  proveedor_id: number;
  forma_pago: string;
  estado?: string;
  impuesto_tasa?: number;
  fecha?: string;
  items: PurchaseRecordItemPayload[];
};

export type PurchaseVendorHistory = {
  proveedor: PurchaseVendor;
  compras: PurchaseRecord[];
  total: number;
  impuesto: number;
  registros: number;
};

export type PurchaseVendorRanking = {
  vendor_id: number;
  vendor_name: string;
  total: number;
  orders: number;
};

export type PurchaseUserRanking = {
  user_id: number;
  user_name?: string | null;
  total: number;
  orders: number;
};

export type PurchaseStatistics = {
  updated_at: string;
  compras_registradas: number;
  total: number;
  impuesto: number;
  monthly_totals: { label: string; value: number }[];
  top_vendors: PurchaseVendorRanking[];
  top_users: PurchaseUserRanking[];
};

export function listPurchaseOrders(token: string, storeId: number, limit = 50): Promise<PurchaseOrder[]> {
  const params = new URLSearchParams({ limit: String(limit), store_id: String(storeId) });
  return requestCollection<PurchaseOrder>(
    `/purchases/?${params.toString()}`,
    { method: "GET" },
    token,
  );
}

export function getPurchaseOrder(token: string, orderId: number): Promise<PurchaseOrder> {
  return request<PurchaseOrder>(`/purchases/${orderId}`, { method: "GET" }, token);
}

export function createPurchaseOrder(
  token: string,
  payload: PurchaseOrderCreateInput,
  reason: string
): Promise<PurchaseOrder> {
  return request<PurchaseOrder>(
    "/purchases",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function receivePurchaseOrder(
  token: string,
  orderId: number,
  payload: PurchaseReceiveInput,
  reason: string
): Promise<PurchaseOrder> {
  return request<PurchaseOrder>(
    `/purchases/${orderId}/receive`,
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function cancelPurchaseOrder(
  token: string,
  orderId: number,
  reason: string
): Promise<PurchaseOrder> {
  return request<PurchaseOrder>(
    `/purchases/${orderId}/cancel`,
    {
      method: "POST",
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function uploadPurchaseOrderDocument(
  token: string,
  orderId: number,
  file: File,
  reason: string
): Promise<PurchaseOrderDocument> {
  const formData = new FormData();
  formData.append("file", file);
  return request<PurchaseOrderDocument>(
    `/purchases/${orderId}/documents`,
    {
      method: "POST",
      body: formData,
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function transitionPurchaseOrderStatus(
  token: string,
  orderId: number,
  payload: PurchaseOrderStatusUpdateInput,
  reason: string
): Promise<PurchaseOrder> {
  return request<PurchaseOrder>(
    `/purchases/${orderId}/status`,
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function sendPurchaseOrderEmail(
  token: string,
  orderId: number,
  payload: PurchaseOrderEmailInput
): Promise<PurchaseOrder> {
  return request<PurchaseOrder>(
    `/purchases/${orderId}/send`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token
  );
}

export function registerPurchaseReturn(
  token: string,
  orderId: number,
  payload: PurchaseReturnInput,
  reason: string
): Promise<PurchaseReturn> {
  return request<PurchaseReturn>(
    `/purchases/${orderId}/returns`,
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function importPurchaseOrdersCsv(
  token: string,
  file: File,
  reason: string
): Promise<PurchaseImportResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request<PurchaseImportResponse>(
    "/purchases/import",
    {
      method: "POST",
      body: formData,
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function getPurchaseSuggestions(
  token: string,
  params: { storeId?: number; lookbackDays?: number; minimumStock?: number; planningHorizonDays?: number } = {},
): Promise<PurchaseSuggestionsResponse> {
  const query = new URLSearchParams();
  if (params.storeId != null) {
    query.set("store_id", String(params.storeId));
  }
  if (params.lookbackDays != null) {
    query.set("lookback_days", String(params.lookbackDays));
  }
  if (params.minimumStock != null) {
    query.set("minimum_stock", String(params.minimumStock));
  }
  if (params.planningHorizonDays != null) {
    query.set("planning_horizon_days", String(params.planningHorizonDays));
  }
  const suffix = query.toString();
  const path = suffix ? `/purchases/suggestions?${suffix}` : "/purchases/suggestions";
  return request<PurchaseSuggestionsResponse>(path, { method: "GET" }, token);
}

export function createPurchaseOrderFromSuggestion(
  token: string,
  payload: PurchaseOrderCreateInput,
  reason: string
): Promise<PurchaseOrder> {
  return request<PurchaseOrder>(
    "/purchases/suggestions/orders",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function listPurchaseVendors(
  token: string,
  filters: { query?: string; status?: string; limit?: number } = {}
): Promise<PurchaseVendor[]> {
  const params = new URLSearchParams();
  if (filters.query) {
    params.append("q", filters.query);
  }
  if (filters.status) {
    params.append("estado", filters.status);
  }
  if (typeof filters.limit === "number") {
    params.append("limit", String(filters.limit));
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return requestCollection<PurchaseVendor>(
    `/purchases/vendors${suffix}`,
    { method: "GET" },
    token,
  );
}

export function createPurchaseVendor(
  token: string,
  payload: PurchaseVendorPayload,
  reason: string
): Promise<PurchaseVendor> {
  return request<PurchaseVendor>(
    "/purchases/vendors",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token,
  );
}

export function updatePurchaseVendor(
  token: string,
  vendorId: number,
  payload: PurchaseVendorPayload,
  reason: string
): Promise<PurchaseVendor> {
  return request<PurchaseVendor>(
    `/purchases/vendors/${vendorId}`,
    { method: "PUT", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token,
  );
}

export function setPurchaseVendorStatus(
  token: string,
  vendorId: number,
  payload: PurchaseVendorStatusPayload,
  reason: string
): Promise<PurchaseVendor> {
  return request<PurchaseVendor>(
    `/purchases/vendors/${vendorId}/status`,
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token,
  );
}

export async function exportPurchaseVendorsCsv(
  token: string,
  filters: { query?: string; status?: string } = {},
  reason: string,
): Promise<Blob> {
  const params = new URLSearchParams();
  if (filters.query) {
    params.append("q", filters.query);
  }
  if (filters.status) {
    params.append("estado", filters.status);
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<Blob>(
    `/purchases/vendors/export/csv${suffix}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
}

export function getPurchaseVendorHistory(
  token: string,
  vendorId: number,
  filters: { limit?: number; dateFrom?: string; dateTo?: string } = {}
): Promise<PurchaseVendorHistory> {
  const params = new URLSearchParams();
  if (typeof filters.limit === "number") {
    params.append("limit", String(filters.limit));
  }
  if (filters.dateFrom) {
    params.append("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.append("date_to", filters.dateTo);
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<PurchaseVendorHistory>(
    `/purchases/vendors/${vendorId}/history${suffix}`,
    { method: "GET" },
    token,
  );
}

export function listPurchaseRecords(
  token: string,
  filters: {
    proveedorId?: number;
    usuarioId?: number;
    dateFrom?: string;
    dateTo?: string;
    estado?: string;
    query?: string;
    limit?: number;
    offset?: number;
  } = {}
): Promise<PurchaseRecord[]> {
  const params = new URLSearchParams();
  if (filters.proveedorId) {
    params.append("proveedor_id", String(filters.proveedorId));
  }
  if (filters.usuarioId) {
    params.append("usuario_id", String(filters.usuarioId));
  }
  if (filters.dateFrom) {
    params.append("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.append("date_to", filters.dateTo);
  }
  if (filters.estado) {
    params.append("estado", filters.estado);
  }
  if (filters.query) {
    params.append("q", filters.query);
  }
  if (typeof filters.limit === "number") {
    params.append("limit", String(filters.limit));
  }
  if (typeof filters.offset === "number") {
    params.append("offset", String(filters.offset));
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return requestCollection<PurchaseRecord>(
    `/purchases/records${suffix}`,
    { method: "GET" },
    token,
  );
}

export function createPurchaseRecord(
  token: string,
  payload: PurchaseRecordPayload,
  reason: string
): Promise<PurchaseRecord> {
  return request<PurchaseRecord>(
    "/purchases/records",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token,
  );
}

export function exportPurchaseRecordsPdf(
  token: string,
  filters: {
    proveedorId?: number;
    usuarioId?: number;
    dateFrom?: string;
    dateTo?: string;
    estado?: string;
    query?: string;
  } = {},
  reason: string,
): Promise<Blob> {
  const params = new URLSearchParams();
  if (filters.proveedorId) {
    params.append("proveedor_id", String(filters.proveedorId));
  }
  if (filters.usuarioId) {
    params.append("usuario_id", String(filters.usuarioId));
  }
  if (filters.dateFrom) {
    params.append("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.append("date_to", filters.dateTo);
  }
  if (filters.estado) {
    params.append("estado", filters.estado);
  }
  if (filters.query) {
    params.append("q", filters.query);
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<Blob>(
    `/purchases/records/export/pdf${suffix}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
}

export function exportPurchaseRecordsExcel(
  token: string,
  filters: {
    proveedorId?: number;
    usuarioId?: number;
    dateFrom?: string;
    dateTo?: string;
    estado?: string;
    query?: string;
  } = {},
  reason: string,
): Promise<Blob> {
  const params = new URLSearchParams();
  if (filters.proveedorId) {
    params.append("proveedor_id", String(filters.proveedorId));
  }
  if (filters.usuarioId) {
    params.append("usuario_id", String(filters.usuarioId));
  }
  if (filters.dateFrom) {
    params.append("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.append("date_to", filters.dateTo);
  }
  if (filters.estado) {
    params.append("estado", filters.estado);
  }
  if (filters.query) {
    params.append("q", filters.query);
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<Blob>(
    `/purchases/records/export/xlsx${suffix}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
}

export function getPurchaseStatistics(
  token: string,
  filters: { dateFrom?: string; dateTo?: string; topLimit?: number } = {}
): Promise<PurchaseStatistics> {
  const params = new URLSearchParams();
  if (filters.dateFrom) {
    params.append("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.append("date_to", filters.dateTo);
  }
  if (typeof filters.topLimit === "number") {
    params.append("top_limit", String(filters.topLimit));
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<PurchaseStatistics>(`/purchases/statistics${suffix}`, { method: "GET" }, token);
}
