// src/services/sales/pos.ts
import { httpPost, httpGet } from "../http";
import { Totals, CheckoutRequest, CheckoutResponse } from "./types";
import { apiMap } from "./apiMap";

export async function priceDraft(dto: CheckoutRequest): Promise<Totals> {
  return httpPost<Totals>(apiMap.pos.price, dto, { withAuth: true });
}

export async function holdSale(dto: CheckoutRequest): Promise<{ holdId: string }> {
  return httpPost<{ holdId: string }>(apiMap.pos.hold, dto, { withAuth: true });
}

export async function resumeHold(holdId: string): Promise<CheckoutRequest> {
  return httpGet<CheckoutRequest>(apiMap.pos.resume(holdId), { withAuth: true });
}

export async function checkout(dto: CheckoutRequest): Promise<CheckoutResponse> {
  return httpPost<CheckoutResponse>(apiMap.pos.checkout, dto, { withAuth: true });
}
