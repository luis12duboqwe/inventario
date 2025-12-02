import { httpClient } from "@api/http";
import { CashSummary, CashClosePayload } from "./types";
import { apiMap } from "./apiMap";

export async function getCashSummary(date: string): Promise<CashSummary> {
  const response = await httpClient.get<CashSummary>(apiMap.cash.summary, { params: { date } });
  return response.data;
}

export async function closeCash(payload: CashClosePayload): Promise<{ ok: true }> {
  const response = await httpClient.post<{ ok: true }>(apiMap.cash.close, payload);
  return response.data;
}
