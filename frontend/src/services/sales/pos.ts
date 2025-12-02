import { httpClient } from "@api/http";
import {
  Totals,
  CheckoutRequest,
  CheckoutResponse,
  PosPromotionsConfig,
  PosPromotionsUpdate,
  ReceiptDeliveryPayload,
  ReceiptDeliveryResponse,
} from "./types";
import { apiMap } from "./apiMap";

export async function priceDraft(dto: CheckoutRequest): Promise<Totals> {
  const response = await httpClient.post<Totals>(apiMap.pos.price, dto);
  return response.data;
}

export async function holdSale(dto: CheckoutRequest): Promise<{ holdId: string }> {
  const response = await httpClient.post<{ holdId: string }>(apiMap.pos.hold, dto);
  return response.data;
}

export async function resumeHold(holdId: string): Promise<CheckoutRequest> {
  const response = await httpClient.get<CheckoutRequest>(apiMap.pos.resume(holdId));
  return response.data;
}

export async function checkout(dto: CheckoutRequest): Promise<CheckoutResponse> {
  const response = await httpClient.post<CheckoutResponse>(apiMap.pos.checkout, dto);
  return response.data;
}

const PROMOTION_REASON_HEADER = { "X-Reason": "Panel promociones POS" } as const;

export async function getPromotions(storeId: string | number): Promise<PosPromotionsConfig> {
  const response = await httpClient.get<PosPromotionsConfig>(apiMap.pos.promotions, {
    headers: PROMOTION_REASON_HEADER,
    params: { store_id: storeId },
  });
  return response.data;
}

export async function updatePromotions(dto: PosPromotionsUpdate): Promise<PosPromotionsConfig> {
  const response = await httpClient.put<PosPromotionsConfig>(apiMap.pos.promotions, dto, {
    headers: PROMOTION_REASON_HEADER,
  });
  return response.data;
}

export async function sendReceipt(
  saleId: string | number,
  payload: ReceiptDeliveryPayload,
  reason: string,
): Promise<ReceiptDeliveryResponse> {
  const response = await httpClient.post<ReceiptDeliveryResponse>(apiMap.pos.sendReceipt(saleId), payload, {
    headers: { "X-Reason": reason },
  });
  return response.data;
}
