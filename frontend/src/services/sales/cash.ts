// src/services/sales/cash.ts
import { httpGet, httpPost } from "../http";
import { CashSummary, CashClosePayload } from "./types";
import { apiMap } from "./apiMap";

export async function getCashSummary(date: string): Promise<CashSummary> {
  return httpGet<CashSummary>(apiMap.cash.summary, { withAuth: true, query: { date } });
}

export async function closeCash(payload: CashClosePayload): Promise<{ ok: true }> {
  return httpPost<{ ok: true }>(apiMap.cash.close, payload, { withAuth: true });
}
