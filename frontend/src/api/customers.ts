import { request, requestCollection } from "./client";
import { ContactHistoryEntry, PaymentMethod } from "./types";
export type { PaymentMethod };

export type Customer = {
  id: number;
  name: string;
  contact_name?: string | null;
  email?: string | null;
  phone: string;
  address?: string | null;
  customer_type: string;
  status: string;
  segment_category?: string | null;
  tags: string[];
  tax_id: string;
  credit_limit: number;
  notes?: string | null;
  outstanding_debt: number;
  history: ContactHistoryEntry[];
  last_interaction_at?: string | null;
  created_at: string;
  updated_at: string;
  privacy_consents: Record<string, boolean>;
  privacy_metadata: Record<string, unknown>;
  privacy_last_request_at?: string | null;
  annual_purchase_amount: number;
  orders_last_year: number;
  purchase_frequency: string;
  segment_labels: string[];
  last_purchase_at?: string | null;
};

export type CustomerPayload = {
  name: string;
  contact_name?: string;
  email?: string;
  phone: string;
  address?: string;
  customer_type?: string;
  status?: string;
  tax_id: string;
  segment_category?: string;
  tags?: string[];
  credit_limit?: number;
  notes?: string;
  outstanding_debt?: number;
  history?: ContactHistoryEntry[];
};

export type CustomerListOptions = {
  limit?: number;
  query?: string;
  status?: string;
  customerType?: string;
  hasDebt?: boolean;
  statusFilter?: string;
  customerTypeFilter?: string;
  segmentCategory?: string;
  tags?: string[];
};

export type CustomerLedgerEntryType = "sale" | "payment" | "adjustment" | "note";

export type CustomerLedgerEntry = {
  id: number;
  entry_type: CustomerLedgerEntryType;
  reference_type?: string | null;
  reference_id?: string | null;
  amount: number;
  balance_after: number;
  note?: string | null;
  details: Record<string, unknown>;
  created_at: string;
  created_by?: string | null;
};

export type CustomerDebtSnapshot = {
  previous_balance: number;
  new_charges: number;
  payments_applied: number;
  remaining_balance: number;
};

export type CreditScheduleEntry = {
  sequence: number;
  due_date: string;
  amount: number;
  status: "pending" | "due_soon" | "overdue";
  reminder?: string | null;
};

export type AccountsReceivableEntry = {
  ledger_entry_id: number;
  reference_type?: string | null;
  reference_id?: string | null;
  reference?: string | null;
  issued_at: string;
  original_amount: number;
  balance_due: number;
  days_outstanding: number;
  status: "current" | "overdue";
  note?: string | null;
  details?: Record<string, unknown> | null;
};

export type AccountsReceivableBucket = {
  label: string;
  days_from: number;
  days_to?: number | null;
  amount: number;
  percentage: number;
  count: number;
};

export type AccountsReceivableSummary = {
  total_outstanding: number;
  available_credit: number;
  credit_limit: number;
  last_payment_at?: string | null;
  next_due_date?: string | null;
  average_days_outstanding: number;
  contact_email?: string | null;
  contact_phone?: string | null;
};

export type CustomerAccountsReceivable = {
  customer: Customer;
  summary: AccountsReceivableSummary;
  aging: AccountsReceivableBucket[];
  open_entries: AccountsReceivableEntry[];
  credit_schedule: CreditScheduleEntry[];
  recent_activity: CustomerLedgerEntry[];
  generated_at: string;
};

export type CustomerPaymentReceipt = {
  ledger_entry: CustomerLedgerEntry;
  debt_summary: CustomerDebtSnapshot;
  credit_schedule: CreditScheduleEntry[];
  receipt_pdf_base64: string;
};

export type CustomerSaleSummary = {
  sale_id: number;
  store_id: number;
  store_name?: string | null;
  payment_method: PaymentMethod;
  status: string;
  subtotal_amount: number;
  tax_amount: number;
  total_amount: number;
  created_at: string;
};

export type CustomerInvoiceSummary = {
  sale_id: number;
  invoice_number: string;
  total_amount: number;
  status: string;
  created_at: string;
  store_id: number;
};

export type StoreCreditRedemption = {
  id: number;
  store_credit_id: number;
  sale_id: number | null;
  amount: number;
  notes?: string | null;
  created_at: string;
  created_by?: string | null;
};

export type StoreCredit = {
  id: number;
  code: string;
  customer_id: number;
  issued_amount: number;
  balance_amount: number;
  status: "ACTIVO" | "PARCIAL" | "REDIMIDO" | "CANCELADO";
  notes?: string | null;
  context: Record<string, unknown>;
  issued_at: string;
  redeemed_at?: string | null;
  expires_at?: string | null;
  redemptions: StoreCreditRedemption[];
};

export type CustomerPrivacyRequest = {
  id: number;
  customer_id: number;
  request_type: "consent" | "anonymization";
  status: "registrada" | "procesada";
  details?: string | null;
  consent_snapshot: Record<string, boolean>;
  masked_fields: string[];
  created_at: string;
  processed_at?: string | null;
  processed_by_id?: number | null;
};

export type CustomerPrivacyRequestCreate = {
  request_type: "consent" | "anonymization";
  details?: string;
  consent?: Record<string, boolean>;
  mask_fields?: string[];
};

export type CustomerPrivacyActionResponse = {
  customer: Customer;
  request: CustomerPrivacyRequest;
};

export type CustomerFinancialSnapshot = {
  credit_limit: number;
  outstanding_debt: number;
  available_credit: number;
  total_sales_credit: number;
  total_payments: number;
  store_credit_issued: number;
  store_credit_available: number;
  store_credit_redeemed: number;
};

export type CustomerSummary = {
  customer: Customer;
  totals: CustomerFinancialSnapshot;
  sales: CustomerSaleSummary[];
  invoices: CustomerInvoiceSummary[];
  payments: CustomerLedgerEntry[];
  ledger: CustomerLedgerEntry[];
  store_credits: StoreCredit[];
  privacy_requests: CustomerPrivacyRequest[];
};

export type CustomerPortfolioItem = {
  customer_id: number;
  name: string;
  status: string;
  customer_type: string;
  credit_limit: number;
  outstanding_debt: number;
  available_credit: number;
  sales_total: number;
  sales_count: number;
  last_sale_at?: string | null;
  last_interaction_at?: string | null;
};

export type CustomerPortfolioTotals = {
  customers: number;
  moroso_flagged: number;
  outstanding_debt: number;
  sales_total: number;
};

export type CustomerPortfolioReport = {
  generated_at: string;
  category: "delinquent" | "frequent";
  filters: {
    category: "delinquent" | "frequent";
    date_from?: string | null;
    date_to?: string | null;
    limit: number;
  };
  items: CustomerPortfolioItem[];
  totals: CustomerPortfolioTotals;
};

export type CustomerLeaderboardEntry = {
  customer_id: number;
  name: string;
  status: string;
  customer_type: string;
  sales_total: number;
  sales_count: number;
  last_sale_at?: string | null;
  outstanding_debt: number;
};

export type CustomerDelinquentSummary = {
  customers_with_debt: number;
  moroso_flagged: number;
  total_outstanding_debt: number;
};

export type CustomerDashboardMetrics = {
  generated_at: string;
  months: number;
  new_customers_per_month: { label: string; value: number }[];
  top_customers: CustomerLeaderboardEntry[];
  delinquent_summary: CustomerDelinquentSummary;
};

export type CustomerPaymentPayload = {
  amount: number;
  method?: string;
  reference?: string | null;
  note?: string | null;
  sale_id?: number | null;
};

export function listCustomers(
  token: string,
  options: CustomerListOptions = {}
): Promise<Customer[]> {
  const params = new URLSearchParams();
  params.append("limit", String(options.limit ?? 100));
  if (options.query) {
    params.append("q", options.query);
  }
  if (options.status) {
    params.append("status", options.status);
  }
  if (options.customerType) {
    params.append("customer_type", options.customerType);
  }
  if (typeof options.hasDebt === "boolean") {
    params.append("has_debt", String(options.hasDebt));
  }
  if (options.statusFilter) {
    params.append("status_filter", options.statusFilter);
  }
  if (options.customerTypeFilter) {
    params.append("customer_type_filter", options.customerTypeFilter);
  }
  if (options.segmentCategory) {
    params.append("segment_category", options.segmentCategory);
  }
  if (Array.isArray(options.tags)) {
    options.tags.forEach((tag) => {
      if (tag.trim()) {
        params.append("tags", tag.trim());
      }
    });
  }
  const queryString = params.toString();
  return requestCollection<Customer>(`/customers?${queryString}`, { method: "GET" }, token);
}

export function exportCustomersCsv(
  token: string,
  options: CustomerListOptions = {},
  reason: string
): Promise<Blob> {
  const params = new URLSearchParams({ export: "csv" });
  if (options.query) {
    params.append("q", options.query);
  }
  if (options.status) {
    params.append("status", options.status);
  }
  if (options.customerType) {
    params.append("customer_type", options.customerType);
  }
  if (typeof options.hasDebt === "boolean") {
    params.append("has_debt", String(options.hasDebt));
  }
  if (options.statusFilter) {
    params.append("status_filter", options.statusFilter);
  }
  if (options.customerTypeFilter) {
    params.append("customer_type_filter", options.customerTypeFilter);
  }
  if (options.segmentCategory) {
    params.append("segment_category", options.segmentCategory);
  }
  if (Array.isArray(options.tags)) {
    options.tags.forEach((tag) => {
      if (tag.trim()) {
        params.append("tags", tag.trim());
      }
    });
  }
  const queryString = params.toString();
  return request<Blob>(
    `/customers?${queryString}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token
  );
}

export function exportCustomerSegment(
  token: string,
  segment: string,
  reason: string,
  format: "csv" = "csv"
): Promise<Blob> {
  const params = new URLSearchParams({ segment, format });
  const queryString = params.toString();
  return request<Blob>(
    `/customers/segments/export?${queryString}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token
  );
}

export function getCustomerPortfolio(
  token: string,
  params: {
    category?: "delinquent" | "frequent";
    limit?: number;
    dateFrom?: string;
    dateTo?: string;
  } = {}
): Promise<CustomerPortfolioReport> {
  const searchParams = new URLSearchParams();
  searchParams.append("category", params.category ?? "delinquent");
  if (typeof params.limit === "number") {
    searchParams.append("limit", String(params.limit));
  }
  if (params.dateFrom) {
    searchParams.append("date_from", params.dateFrom);
  }
  if (params.dateTo) {
    searchParams.append("date_to", params.dateTo);
  }
  const queryString = searchParams.toString();
  return request<CustomerPortfolioReport>(
    `/reports/customers/portfolio?${queryString}`,
    { method: "GET" },
    token
  );
}

export function exportCustomerPortfolioPdf(
  token: string,
  params: {
    category?: "delinquent" | "frequent";
    limit?: number;
    dateFrom?: string;
    dateTo?: string;
  },
  reason: string
): Promise<Blob> {
  const searchParams = new URLSearchParams({ export: "pdf" });
  searchParams.append("category", params.category ?? "delinquent");
  if (typeof params.limit === "number") {
    searchParams.append("limit", String(params.limit));
  }
  if (params.dateFrom) {
    searchParams.append("date_from", params.dateFrom);
  }
  if (params.dateTo) {
    searchParams.append("date_to", params.dateTo);
  }
  return request<Blob>(
    `/reports/customers/portfolio?${searchParams.toString()}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token
  );
}

export function exportCustomerPortfolioExcel(
  token: string,
  params: {
    category?: "delinquent" | "frequent";
    limit?: number;
    dateFrom?: string;
    dateTo?: string;
  },
  reason: string
): Promise<Blob> {
  const searchParams = new URLSearchParams({ export: "xlsx" });
  searchParams.append("category", params.category ?? "delinquent");
  if (typeof params.limit === "number") {
    searchParams.append("limit", String(params.limit));
  }
  if (params.dateFrom) {
    searchParams.append("date_from", params.dateFrom);
  }
  if (params.dateTo) {
    searchParams.append("date_to", params.dateTo);
  }
  return request<Blob>(
    `/reports/customers/portfolio?${searchParams.toString()}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token
  );
}

export function getCustomerDashboardMetrics(
  token: string,
  params: { months?: number; topLimit?: number } = {}
): Promise<CustomerDashboardMetrics> {
  const searchParams = new URLSearchParams();
  if (typeof params.months === "number") {
    searchParams.append("months", String(params.months));
  }
  if (typeof params.topLimit === "number") {
    searchParams.append("top_limit", String(params.topLimit));
  }
  const suffix = searchParams.toString();
  const query = suffix ? `?${suffix}` : "";
  return request<CustomerDashboardMetrics>(
    `/customers/dashboard${query}`,
    { method: "GET" },
    token
  );
}

export function createCustomer(
  token: string,
  payload: CustomerPayload,
  reason: string
): Promise<Customer> {
  return request<Customer>(
    "/customers",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function updateCustomer(
  token: string,
  customerId: number,
  payload: Partial<CustomerPayload>,
  reason: string
): Promise<Customer> {
  return request<Customer>(
    `/customers/${customerId}`,
    { method: "PUT", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function deleteCustomer(token: string, customerId: number, reason: string): Promise<void> {
  return request<void>(
    `/customers/${customerId}`,
    { method: "DELETE", headers: { "X-Reason": reason } },
    token
  );
}

export function appendCustomerNote(
  token: string,
  customerId: number,
  note: string,
  reason: string
): Promise<Customer> {
  return request<Customer>(
    `/customers/${customerId}/notes`,
    {
      method: "POST",
      body: JSON.stringify({ note }),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function createCustomerPrivacyRequest(
  token: string,
  customerId: number,
  payload: CustomerPrivacyRequestCreate,
  reason: string
): Promise<CustomerPrivacyActionResponse> {
  return request<CustomerPrivacyActionResponse>(
    `/customers/${customerId}/privacy-requests`,
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function registerCustomerPayment(
  token: string,
  customerId: number,
  payload: CustomerPaymentPayload,
  reason: string
): Promise<CustomerPaymentReceipt> {
  return request<CustomerPaymentReceipt>(
    `/customers/${customerId}/payments`,
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function getCustomerSummary(token: string, customerId: number): Promise<CustomerSummary> {
  return request<CustomerSummary>(
    `/customers/${customerId}/summary`,
    { method: "GET" },
    token
  );
}

export function getCustomerAccountsReceivable(
  token: string,
  customerId: number,
): Promise<CustomerAccountsReceivable> {
  return request<CustomerAccountsReceivable>(
    `/customers/${customerId}/accounts-receivable`,
    { method: "GET" },
    token,
  );
}

export function downloadCustomerStatement(
  token: string,
  customerId: number,
  reason: string,
): Promise<Blob> {
  return request<Blob>(
    `/customers/${customerId}/accounts-receivable/statement.pdf`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
}
