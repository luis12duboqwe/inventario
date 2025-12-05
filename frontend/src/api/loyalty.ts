import { request, requestCollection } from "./client";

export type LoyaltyTransactionType = "ACCRUAL" | "REDEMPTION" | "ADJUSTMENT" | "EXPIRATION";

export type LoyaltyAccount = {
  id: number;
  customer_id: number;
  balance_points: number;
  lifetime_points_earned: number;
  lifetime_points_redeemed: number;
  expired_points_total: number;
  accrual_rate: number;
  redemption_rate: number;
  expiration_days: number;
  is_active: boolean;
  rule_config: Record<string, unknown>;
  last_accrual_at?: string | null;
  last_redemption_at?: string | null;
  last_expiration_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type LoyaltyTransaction = {
  id: number;
  account_id: number;
  sale_id?: number | null;
  transaction_type: LoyaltyTransactionType;
  points: number;
  balance_after: number;
  currency_amount: number;
  description?: string | null;
  details: Record<string, unknown>;
  registered_at: string;
  expires_at?: string | null;
  registered_by_id?: number | null;
};

export type LoyaltyReportSummary = {
  total_accounts: number;
  active_accounts: number;
  inactive_accounts: number;
  total_balance: number;
  total_earned: number;
  total_redeemed: number;
  total_expired: number;
  last_activity?: string | null;
};

export type LoyaltyAccountUpdatePayload = {
  accrual_rate?: number;
  redemption_rate?: number;
  expiration_days?: number;
  is_active?: boolean;
  rule_config?: Record<string, unknown>;
};

export function listLoyaltyAccounts(
  token: string,
  params: { is_active?: boolean; customer_id?: number } = {}
): Promise<LoyaltyAccount[]> {
  const searchParams = new URLSearchParams();
  if (typeof params.is_active === "boolean") {
    searchParams.set("is_active", String(params.is_active));
  }
  if (typeof params.customer_id === "number") {
    searchParams.set("customer_id", String(params.customer_id));
  }
  const query = searchParams.toString();
  const suffix = query ? `?${query}` : "";
  return requestCollection<LoyaltyAccount>(`/loyalty/accounts${suffix}`, { method: "GET" }, token);
}

export function getLoyaltyAccount(token: string, customerId: number): Promise<LoyaltyAccount> {
  return request<LoyaltyAccount>(`/loyalty/accounts/${customerId}`, { method: "GET" }, token);
}

export function updateLoyaltyAccount(
  token: string,
  customerId: number,
  payload: LoyaltyAccountUpdatePayload,
  reason: string
): Promise<LoyaltyAccount> {
  return request<LoyaltyAccount>(
    `/loyalty/accounts/${customerId}`,
    { method: "PUT", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function listLoyaltyTransactions(
  token: string,
  params: {
    account_id?: number;
    customer_id?: number;
    sale_id?: number;
    limit?: number;
    offset?: number;
  } = {}
): Promise<LoyaltyTransaction[]> {
  const searchParams = new URLSearchParams();
  if (typeof params.account_id === "number") {
    searchParams.set("account_id", String(params.account_id));
  }
  if (typeof params.customer_id === "number") {
    searchParams.set("customer_id", String(params.customer_id));
  }
  if (typeof params.sale_id === "number") {
    searchParams.set("sale_id", String(params.sale_id));
  }
  if (typeof params.limit === "number") {
    searchParams.set("limit", String(params.limit));
  }
  if (typeof params.offset === "number") {
    searchParams.set("offset", String(params.offset));
  }
  const query = searchParams.toString();
  const suffix = query ? `?${query}` : "";
  return requestCollection<LoyaltyTransaction>(
    `/loyalty/transactions${suffix}`,
    { method: "GET" },
    token
  );
}

export function getLoyaltySummary(token: string): Promise<LoyaltyReportSummary> {
  return request<LoyaltyReportSummary>("/loyalty/reports/summary", { method: "GET" }, token);
}
