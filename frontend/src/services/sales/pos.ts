// src/services/sales/pos.ts
import { httpPost } from "@/services/http";
import { Totals, CheckoutRequest, CheckoutResponse } from "./types";
import { apiMap } from "./apiMap";

export async function priceDraft(saleId: string | number, dto: CheckoutRequest): Promise<Totals> {
  return httpPost<Totals>(apiMap.pos.price(saleId), dto, { withAuth: true });
}

export async function holdSale(saleId: string | number, dto: CheckoutRequest): Promise<{ holdId: string }> {
  return httpPost<{ holdId: string }>(apiMap.pos.hold(saleId), dto, { withAuth: true });
}

export async function resumeHold(saleId: string | number): Promise<CheckoutRequest> {
  return httpPost<CheckoutRequest>(apiMap.pos.resume(saleId), undefined, { withAuth: true });
}

export async function checkout(saleId: string | number, dto: CheckoutRequest): Promise<CheckoutResponse> {
  return httpPost<CheckoutResponse>(apiMap.pos.checkout(saleId), dto, { withAuth: true });
}
