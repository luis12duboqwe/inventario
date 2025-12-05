import { request } from "./client";
import { PaymentMethod } from "./types";
export type { PaymentMethod };

export type PaymentCenter = {
  id: number;
  name: string;
  type: "CASH" | "CARD" | "TRANSFER" | "CHECK" | "OTHER";
  status: "ACTIVE" | "INACTIVE";
  balance: number;
  currency: string;
  metadata?: Record<string, unknown>;
};

export type PaymentCenterInput = {
  name: string;
  type: PaymentCenter["type"];
  status?: PaymentCenter["status"];
  currency?: string;
  metadata?: Record<string, unknown>;
};

export type PaymentCenterTransaction = {
  id: number;
  type: "PAYMENT" | "REFUND" | "CREDIT_NOTE";
  amount: number;
  created_at: string;
  order_id?: number | null;
  order_number?: string | null;
  customer_id?: number | null;
  customer_name?: string | null;
  method?: PaymentMethod | null;
  note?: string | null;
  status?: "POSTED" | "VOID";
};

export type PaymentCenterSummary = {
  collections_today: number;
  collections_month: number;
  pending_balance: number;
  refunds_month: number;
};

export type PaymentCenterResponse = {
  summary: PaymentCenterSummary;
  transactions: PaymentCenterTransaction[];
};

export type PaymentCenterFilters = {
  limit?: number;
  query?: string;
  dateFrom?: string;
  dateTo?: string;
  method?: PaymentMethod;
  type?: string;
};

export type PaymentCenterPaymentInput = {
  customer_id: number;
  amount: number;
  method: PaymentMethod;
  reference?: string;
  sale_id?: number;
};

export type PaymentCenterRefundInput = {
  customer_id: number;
  amount: number;
  method: PaymentMethod;
  reason: string;
  note: string;
  sale_id?: number;
};

export type PaymentCenterCreditNoteLine = {
  description: string;
  quantity: number;
  amount: number;
};

export type PaymentCenterCreditNoteInput = {
  customer_id: number;
  total: number;
  lines: PaymentCenterCreditNoteLine[];
  note: string;
  sale_id?: number;
};

export function getPaymentCenters(token: string): Promise<PaymentCenter[]> {
  return request<PaymentCenter[]>("/payments/centers", { method: "GET" }, token);
}

export function createPaymentCenter(
  token: string,
  payload: PaymentCenterInput,
  reason: string
): Promise<PaymentCenter> {
  return request(
    "/payments/centers",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function updatePaymentCenter(
  token: string,
  id: number,
  payload: Partial<PaymentCenterInput>,
  reason: string
): Promise<PaymentCenter> {
  return request(
    `/payments/centers/${id}`,
    { method: "PUT", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function getPaymentCenter(
  token: string,
  filters: PaymentCenterFilters = {}
): Promise<PaymentCenterResponse> {
  const params = new URLSearchParams();
  if (filters.limit) params.set("limit", String(filters.limit));
  if (filters.query) params.set("query", filters.query);
  if (filters.dateFrom) params.set("date_from", filters.dateFrom);
  if (filters.dateTo) params.set("date_to", filters.dateTo);
  if (filters.method) params.set("method", filters.method);
  if (filters.type) params.set("type", filters.type);

  const query = params.toString();
  const url = query ? `/payments/center?${query}` : "/payments/center";
  return request<PaymentCenterResponse>(url, { method: "GET" }, token);
}

export function registerPaymentCenterPayment(
  token: string,
  payload: PaymentCenterPaymentInput,
  reason: string
): Promise<void> {
  return request(
    "/payments/center/transactions/payment",
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function registerPaymentCenterRefund(
  token: string,
  payload: PaymentCenterRefundInput,
  reason: string
): Promise<void> {
  return request(
    "/payments/center/transactions/refund",
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function registerPaymentCenterCreditNote(
  token: string,
  payload: PaymentCenterCreditNoteInput,
  reason: string
): Promise<void> {
  return request(
    "/payments/center/transactions/credit-note",
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}
