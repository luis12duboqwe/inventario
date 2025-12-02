import { request, requestCollection } from "./client";
import { ContactHistoryEntry } from "./types";

export type SupplierContact = {
  name?: string | null;
  position?: string | null;
  email?: string | null;
  phone?: string | null;
  notes?: string | null;
};

export type Supplier = {
  id: number;
  name: string;
  rtn?: string | null;
  payment_terms?: string | null;
  contact_name?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  notes?: string | null;
  outstanding_debt: number;
  history: ContactHistoryEntry[];
  contact_info: SupplierContact[];
  products_supplied: string[];
  created_at: string;
  updated_at: string;
};

export type SupplierPayload = {
  name: string;
  rtn?: string | null;
  payment_terms?: string | null;
  contact_name?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  notes?: string | null;
  outstanding_debt?: number;
  history?: ContactHistoryEntry[];
  contact_info?: SupplierContact[];
  products_supplied?: string[];
};

export type SupplierBatch = {
  id: number;
  supplier_id: number;
  store_id?: number | null;
  device_id?: number | null;
  model_name: string;
  batch_code: string;
  unit_cost: number;
  quantity: number;
  purchase_date: string;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type SupplierBatchPayload = {
  store_id?: number | null;
  device_id?: number | null;
  model_name: string;
  batch_code: string;
  unit_cost: number;
  quantity?: number;
  purchase_date: string;
  notes?: string | null;
};

export type SupplierBatchOverviewItem = {
  supplier_id: number;
  supplier_name: string;
  batch_count: number;
  total_quantity: number;
  total_value: number;
  latest_purchase_date: string;
  latest_batch_code?: string | null;
  latest_unit_cost?: number | null;
};

export type SupplierAccountsPayableBucket = {
  label: string;
  days_from: number;
  days_to: number | null;
  amount: number;
  percentage: number;
  count: number;
};

export type SupplierAccountsPayableSupplier = {
  supplier_id: number;
  supplier_name: string;
  rtn?: string | null;
  payment_terms?: string | null;
  outstanding_debt: number;
  bucket_label: string;
  bucket_from: number;
  bucket_to: number | null;
  days_outstanding: number;
  last_activity?: string | null;
  contact_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  products_supplied: string[];
  contact_info: SupplierContact[];
};

export type SupplierAccountsPayableSummary = {
  total_balance: number;
  total_overdue: number;
  supplier_count: number;
  generated_at: string;
  buckets: SupplierAccountsPayableBucket[];
};

export type SupplierAccountsPayableResponse = {
  summary: SupplierAccountsPayableSummary;
  suppliers: SupplierAccountsPayableSupplier[];
};

export function listSuppliers(
  token: string,
  query?: string,
  limit = 100
): Promise<Supplier[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (query) {
    params.append("q", query);
  }
  return requestCollection<Supplier>(`/suppliers?${params.toString()}`, { method: "GET" }, token);
}

export function getSuppliersAccountsPayable(
  token: string
): Promise<SupplierAccountsPayableResponse> {
  return request<SupplierAccountsPayableResponse>(
    "/suppliers/accounts-payable",
    { method: "GET" },
    token
  );
}

export function exportSuppliersCsv(token: string, query?: string): Promise<Blob> {
  const params = new URLSearchParams({ export: "csv" });
  if (query) {
    params.append("q", query);
  }
  return request<Blob>(`/suppliers?${params.toString()}`, { method: "GET" }, token);
}

export function createSupplier(
  token: string,
  payload: SupplierPayload,
  reason: string
): Promise<Supplier> {
  return request<Supplier>(
    "/suppliers",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function updateSupplier(
  token: string,
  supplierId: number,
  payload: Partial<SupplierPayload>,
  reason: string
): Promise<Supplier> {
  return request<Supplier>(
    `/suppliers/${supplierId}`,
    { method: "PUT", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function deleteSupplier(token: string, supplierId: number, reason: string): Promise<void> {
  return request<void>(
    `/suppliers/${supplierId}`,
    { method: "DELETE", headers: { "X-Reason": reason } },
    token
  );
}

export function getSupplierBatchOverview(
  token: string,
  storeId: number,
  limit = 5,
): Promise<SupplierBatchOverviewItem[]> {
  return requestCollection<SupplierBatchOverviewItem>(
    `/reports/inventory/supplier-batches?store_id=${storeId}&limit=${limit}`,
    { method: "GET" },
    token,
  );
}

export function listSupplierBatches(
  token: string,
  supplierId: number,
  limit = 50
): Promise<SupplierBatch[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  return requestCollection<SupplierBatch>(
    `/suppliers/${supplierId}/batches?${params.toString()}`,
    { method: "GET" },
    token
  );
}

export function createSupplierBatch(
  token: string,
  supplierId: number,
  payload: SupplierBatchPayload,
  reason: string
): Promise<SupplierBatch> {
  return request<SupplierBatch>(
    `/suppliers/${supplierId}/batches`,
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function updateSupplierBatch(
  token: string,
  batchId: number,
  payload: Partial<SupplierBatchPayload>,
  reason: string
): Promise<SupplierBatch> {
  return request<SupplierBatch>(
    `/suppliers/batches/${batchId}`,
    { method: "PUT", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function deleteSupplierBatch(token: string, batchId: number, reason: string): Promise<void> {
  return request<void>(
    `/suppliers/batches/${batchId}`,
    { method: "DELETE", headers: { "X-Reason": reason } },
    token
  );
}
