import httpClient from "./http";

export type PriceListItem = {
  id: number;
  price_list_id: number;
  device_id: number;
  price: number;
  currency: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type PriceList = {
  id: number;
  name: string;
  description: string | null;
  priority: number;
  is_active: boolean;
  store_id: number | null;
  customer_id: number | null;
  starts_at: string | null;
  ends_at: string | null;
  scope: string;
  created_at: string;
  updated_at: string;
  items: PriceListItem[];
};

export type PriceListCreateInput = {
  name: string;
  description?: string | null;
  priority?: number;
  is_active?: boolean;
  store_id?: number | null;
  customer_id?: number | null;
  starts_at?: string | null;
  ends_at?: string | null;
};

export type PriceListUpdateInput = Partial<Omit<PriceListCreateInput, "name">> & {
  name?: string;
};

export type PriceListItemCreateInput = {
  device_id: number;
  price: number;
  currency?: string;
  notes?: string | null;
};

export type PriceListItemUpdateInput = Partial<Omit<PriceListItemCreateInput, "device_id">>;

export type PriceEvaluationRequest = {
  device_id: number;
  store_id?: number;
  customer_id?: number;
};

export type PriceEvaluationResponse = {
  device_id: number;
  price_list_id: number | null;
  scope: string | null;
  price: number | null;
  currency: string | null;
};

export async function listPriceLists(params: {
  storeId?: number | null;
  customerId?: number | null;
  includeInactive?: boolean;
  includeGlobal?: boolean;
}): Promise<PriceList[]> {
  const response = await httpClient.get<PriceList[]>("/pricing/price-lists", {
    params: {
      store_id: params.storeId ?? undefined,
      customer_id: params.customerId ?? undefined,
      include_inactive: params.includeInactive ?? false,
      include_global: params.includeGlobal ?? true,
    },
  });
  return response.data;
}

export async function createPriceList(
  payload: PriceListCreateInput,
  reason: string,
): Promise<PriceList> {
  const response = await httpClient.post<PriceList>("/pricing/price-lists", payload, {
    headers: { "X-Reason": reason },
  });
  return response.data;
}

export async function updatePriceList(
  priceListId: number,
  payload: PriceListUpdateInput,
  reason: string,
): Promise<PriceList> {
  const response = await httpClient.put<PriceList>(
    `/pricing/price-lists/${priceListId}`,
    payload,
    { headers: { "X-Reason": reason } },
  );
  return response.data;
}

export async function deletePriceList(priceListId: number, reason: string): Promise<void> {
  await httpClient.delete(`/pricing/price-lists/${priceListId}`, {
    headers: { "X-Reason": reason },
  });
}

export async function createPriceListItem(
  priceListId: number,
  payload: PriceListItemCreateInput,
  reason: string,
): Promise<PriceListItem> {
  const response = await httpClient.post<PriceListItem>(
    `/pricing/price-lists/${priceListId}/items`,
    payload,
    { headers: { "X-Reason": reason } },
  );
  return response.data;
}

export async function updatePriceListItem(
  priceListId: number,
  itemId: number,
  payload: PriceListItemUpdateInput,
  reason: string,
): Promise<PriceListItem> {
  const response = await httpClient.put<PriceListItem>(
    `/pricing/price-lists/${priceListId}/items/${itemId}`,
    payload,
    { headers: { "X-Reason": reason } },
  );
  return response.data;
}

export async function deletePriceListItem(
  priceListId: number,
  itemId: number,
  reason: string,
): Promise<void> {
  await httpClient.delete(`/pricing/price-lists/${priceListId}/items/${itemId}`, {
    headers: { "X-Reason": reason },
  });
}

export async function evaluatePrice(
  payload: PriceEvaluationRequest,
): Promise<PriceEvaluationResponse> {
  const response = await httpClient.get<PriceEvaluationResponse>(
    "/pricing/price-evaluation",
    {
      params: {
        device_id: payload.device_id,
        store_id: payload.store_id ?? undefined,
        customer_id: payload.customer_id ?? undefined,
      },
    },
  );
  return response.data;
}
