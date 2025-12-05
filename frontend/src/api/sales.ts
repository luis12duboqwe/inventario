import { request, requestCollection } from "./client";
import { PaymentMethod, ReturnDisposition, ReturnReasonCategory, CashSession } from "./types";
import { Customer } from "./customers";

export type SaleStoreSummary = {
  id: number;
  name: string;
  location?: string | null;
};

export type SaleUserSummary = {
  id: number;
  username: string;
  full_name?: string | null;
};

export type SaleDeviceSummary = {
  id: number;
  sku: string;
  name: string;
  modelo?: string | null;
  imei?: string | null;
  serial?: string | null;
};

export type WarrantyStatus = "SIN_GARANTIA" | "ACTIVA" | "VENCIDA" | "RECLAMO" | "RESUELTA";
export type WarrantyClaimStatus = "ABIERTO" | "EN_PROCESO" | "RESUELTO" | "CANCELADO";
export type WarrantyClaimType = "REPARACION" | "REEMPLAZO";

export type WarrantyDeviceSummary = {
  id: number;
  sku: string;
  name: string;
  imei: string | null;
  serial: string | null;
};

export type WarrantySaleSummary = {
  id: number;
  store_id: number;
  customer_id: number | null;
  customer_name: string | null;
  created_at: string;
};

export type WarrantyClaim = {
  id: number;
  claim_type: WarrantyClaimType;
  status: WarrantyClaimStatus;
  notes: string | null;
  opened_at: string;
  resolved_at: string | null;
  repair_order_id: number | null;
  performed_by_id: number | null;
};

export type WarrantyAssignment = {
  id: number;
  sale_item_id: number;
  device_id: number;
  coverage_months: number;
  activation_date: string;
  expiration_date: string;
  status: WarrantyStatus;
  serial_number: string | null;
  activation_channel: string | null;
  created_at: string;
  updated_at: string;
  device: WarrantyDeviceSummary | null;
  sale: WarrantySaleSummary | null;
  claims: WarrantyClaim[];
  remaining_days: number;
  is_expired: boolean;
};

export type WarrantyMetrics = {
  total_assignments: number;
  active_assignments: number;
  expired_assignments: number;
  claims_open: number;
  claims_resolved: number;
  expiring_soon: number;
  average_coverage_days: number;
  generated_at: string;
};

export type WarrantyRepairOrderPayload = {
  store_id: number;
  customer_id?: number | null;
  customer_name?: string | null;
  customer_contact?: string | null;
  technician_name: string;
  damage_type: string;
  diagnosis?: string;
  problem_description?: string;
  device_model?: string;
  imei?: string;
  device_description?: string;
  notes?: string;
  estimated_cost?: number;
  deposit_amount?: number;
  labor_cost?: number;
  parts?: {
    device_id?: number;
    part_name?: string;
    source?: "STOCK" | "EXTERNAL";
    quantity: number;
    unit_cost?: number;
  }[];
};

export type WarrantyClaimPayload = {
  claim_type: WarrantyClaimType;
  notes?: string | null;
  repair_order?: WarrantyRepairOrderPayload | null;
};

export type WarrantyClaimStatusUpdatePayload = {
  status: WarrantyClaimStatus;
  notes?: string | null;
  repair_order_id?: number | null;
};

export type SaleItem = {
  id: number;
  sale_id: number;
  device_id: number;
  quantity: number;
  unit_price: number;
  discount_amount: number;
  total_line: number;
  device?: SaleDeviceSummary | null;
  reservation_id?: number | null;
  warranty_status?: WarrantyStatus | null;
  warranty?: WarrantyAssignment | null;
};

export type SaleReturn = {
  id: number;
  sale_id: number;
  device_id: number;
  quantity: number;
  reason: string;
  reason_category: ReturnReasonCategory;
  disposition: ReturnDisposition;
  warehouse_id?: number | null;
  processed_by_id?: number | null;
  approved_by_id?: number | null;
  approved_by_name?: string | null;
  created_at: string;
};

export type Sale = {
  id: number;
  store_id: number;
  customer_id?: number | null;
  customer_name?: string | null;
  payment_method: PaymentMethod;
  discount_percent: number;
  subtotal_amount: number;
  tax_amount: number;
  total_amount: number;
  notes?: string | null;
  created_at: string;
  performed_by_id?: number | null;
  cash_session_id?: number | null;
  customer?: Customer | null;
  cash_session?: CashSession | null;
  items: SaleItem[];
  returns: SaleReturn[];
  payment_breakdown?: Record<string, number>;
  store?: SaleStoreSummary | null;
  performed_by?: SaleUserSummary | null;
};

export type SaleHistorySearchResponse = {
  by_ticket: Sale[];
  by_date: Sale[];
  by_customer: Sale[];
  by_qr: Sale[];
};

export type SaleHistorySearchFilters = {
  ticket?: string;
  date?: string;
  customer?: string;
  qr?: string;
  limit?: number;
};

export type SalesFilters = {
  storeId?: number | null;
  customerId?: number | null;
  userId?: number | null;
  dateFrom?: string;
  dateTo?: string;
  query?: string;
  limit?: number;
};

export type SaleCreateInput = {
  store_id: number;
  payment_method: PaymentMethod;
  items: {
    device_id: number;
    quantity: number;
    discount_percent?: number;
    batch_code?: string | null;
  }[];
  discount_percent?: number;
  customer_id?: number;
  customer_name?: string;
  notes?: string;
};

export type SaleReturnInput = {
  sale_id: number;
  items: {
    device_id: number;
    quantity: number;
    reason: string;
    disposition?: ReturnDisposition;
    warehouse_id?: number | null;
    category?: ReturnReasonCategory;
  }[];
  approval?: {
    supervisor_username: string;
    pin: string;
  };
};

export type ReturnRecordType = "sale" | "purchase";

export type ReturnRecord = {
  id: number;
  type: ReturnRecordType;
  reference_id: number;
  reference_label: string;
  store_id: number;
  store_name?: string | null;
  warehouse_id?: number | null;
  warehouse_name?: string | null;
  device_id: number;
  device_name?: string | null;
  quantity: number;
  reason: string;
  reason_category: ReturnReasonCategory;
  disposition: ReturnDisposition;
  processed_by_id?: number | null;
  processed_by_name?: string | null;
  approved_by_id?: number | null;
  approved_by_name?: string | null;
  partner_name?: string | null;
  occurred_at: string;
  refund_amount?: number | null;
  payment_method?: PaymentMethod | string | null;
  corporate_reason?: string | null;
  credit_note_amount?: number | null;
};

export type ReturnsTotals = {
  total: number;
  sales: number;
  purchases: number;
  refunds_by_method: Record<string, number>;
  refund_total_amount: number;
  credit_notes_total: number;
  categories: Record<string, number>;
};

export type ReturnsOverview = {
  items: ReturnRecord[];
  totals: ReturnsTotals;
};

export type ReturnsFilters = {
  storeId?: number | null;
  type?: ReturnRecordType;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
  offset?: number;
};

function buildSalesFilterParams(filters: SalesFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (typeof filters.storeId === "number") {
    params.set("store_id", String(filters.storeId));
  }
  if (typeof filters.customerId === "number") {
    params.set("customer_id", String(filters.customerId));
  }
  if (typeof filters.userId === "number") {
    params.set("user_id", String(filters.userId));
  }
  if (filters.dateFrom) {
    params.set("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.set("date_to", filters.dateTo);
  }
  if (filters.query) {
    params.set("query", filters.query);
  }
  return params;
}

export function listSales(token: string, filters: SalesFilters = {}): Promise<Sale[]> {
  const params = buildSalesFilterParams(filters);
  const limit = typeof filters.limit === "number" ? filters.limit : 50;
  params.append("limit", String(limit));
  const query = params.toString();
  const path = `/sales?${query}`;
  return requestCollection<Sale>(path, { method: "GET" }, token);
}

export function searchSalesHistory(
  token: string,
  filters: SaleHistorySearchFilters = {}
): Promise<SaleHistorySearchResponse> {
  const params = new URLSearchParams();
  if (filters.ticket?.trim()) {
    params.set("ticket", filters.ticket.trim());
  }
  if (filters.date) {
    params.set("date", filters.date);
  }
  if (filters.customer?.trim()) {
    params.set("customer", filters.customer.trim());
  }
  if (filters.qr?.trim()) {
    params.set("qr", filters.qr.trim());
  }
  const limitValue = typeof filters.limit === "number" ? filters.limit : undefined;
  if (typeof limitValue === "number") {
    params.set("limit", String(limitValue));
  }
  const query = params.toString();
  const path = query ? `/sales/history/search?${query}` : "/sales/history/search";
  return request<SaleHistorySearchResponse>(path, { method: "GET" }, token);
}

export function createSale(
  token: string,
  payload: SaleCreateInput,
  reason: string
): Promise<Sale> {
  return request<Sale>(
    "/sales",
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function exportSalesPdf(token: string, filters: SalesFilters = {}, reason: string): Promise<Blob> {
  const params = buildSalesFilterParams(filters);
  const query = params.toString();
  const path = query ? `/sales/export/pdf?${query}` : "/sales/export/pdf";
  return request<Blob>(path, { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" }, token);
}

export function exportSalesExcel(token: string, filters: SalesFilters = {}, reason: string): Promise<Blob> {
  const params = buildSalesFilterParams(filters);
  const query = params.toString();
  const path = query ? `/sales/export/xlsx?${query}` : "/sales/export/xlsx";
  return request<Blob>(path, { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" }, token);
}

export function registerSaleReturn(
  token: string,
  payload: SaleReturnInput,
  reason: string
): Promise<SaleReturn[]> {
  return request<SaleReturn[]>(
    "/sales/returns",
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function listReturns(
  token: string,
  filters: ReturnsFilters = {}
): Promise<ReturnsOverview> {
  const params = new URLSearchParams();
  if (typeof filters.storeId === "number") {
    params.set("store_id", String(filters.storeId));
  }
  if (filters.type) {
    params.set("type", filters.type);
  }
  if (filters.dateFrom) {
    params.set("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.set("date_to", filters.dateTo);
  }
  if (typeof filters.limit === "number") {
    params.set("limit", String(filters.limit));
  }
  if (typeof filters.offset === "number") {
    params.set("offset", String(filters.offset));
  }
  const query = params.toString();
  const path = `/returns${query ? `?${query}` : ""}`;
  return request<ReturnsOverview>(path, { method: "GET" }, token);
}

export function listWarranties(
  token: string,
  params: {
    store_id?: number;
    status?: WarrantyStatus;
    q?: string;
    expiring_before?: string;
    limit?: number;
    offset?: number;
  } = {}
): Promise<WarrantyAssignment[]> {
  const searchParams = new URLSearchParams();
  if (typeof params.store_id === "number") {
    searchParams.set("store_id", String(params.store_id));
  }
  if (params.status) {
    searchParams.set("status", params.status);
  }
  if (params.q) {
    searchParams.set("q", params.q);
  }
  if (params.expiring_before) {
    searchParams.set("expiring_before", params.expiring_before);
  }
  if (typeof params.limit === "number") {
    searchParams.set("limit", String(params.limit));
  }
  if (typeof params.offset === "number") {
    searchParams.set("offset", String(params.offset));
  }
  const query = searchParams.toString();
  const suffix = query ? `?${query}` : "";
  return requestCollection<WarrantyAssignment>(`/warranties${suffix}`, { method: "GET" }, token);
}

export function getWarranty(token: string, assignmentId: number): Promise<WarrantyAssignment> {
  return request<WarrantyAssignment>(`/warranties/${assignmentId}`, { method: "GET" }, token);
}

export function getWarrantyMetrics(
  token: string,
  params: { store_id?: number; horizon_days?: number } = {}
): Promise<WarrantyMetrics> {
  const searchParams = new URLSearchParams();
  if (typeof params.store_id === "number") {
    searchParams.set("store_id", String(params.store_id));
  }
  if (typeof params.horizon_days === "number") {
    searchParams.set("horizon_days", String(params.horizon_days));
  }
  const query = searchParams.toString();
  const suffix = query ? `?${query}` : "";
  return request<WarrantyMetrics>(`/warranties/metrics${suffix}`, { method: "GET" }, token);
}

export function createWarrantyClaim(
  token: string,
  assignmentId: number,
  payload: WarrantyClaimPayload,
  reason: string
): Promise<WarrantyAssignment> {
  return request<WarrantyAssignment>(
    `/warranties/${assignmentId}/claims`,
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function updateWarrantyClaimStatus(
  token: string,
  claimId: number,
  payload: WarrantyClaimStatusUpdatePayload,
  reason: string
): Promise<WarrantyAssignment> {
  return request<WarrantyAssignment>(
    `/warranties/claims/${claimId}`,
    { method: "PATCH", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}
export type { ReturnDisposition, ReturnReasonCategory } from "./types";
