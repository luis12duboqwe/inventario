import { request, requestCollection } from "./client";

export type PriceListItem = {
  id: number;
  price_list_id: number;
  device_id: number;
  price: number;
  discount_percentage: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type PriceList = {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  store_id: number | null;
  customer_id: number | null;
  currency: string;
  valid_from: string | null;
  valid_until: string | null;
  created_at: string;
  updated_at: string;
  items: PriceListItem[];
};

export type PriceListCreateInput = {
  name: string;
  description?: string | null;
  is_active?: boolean;
  store_id?: number | null;
  customer_id?: number | null;
  currency?: string;
  valid_from?: string | null;
  valid_until?: string | null;
};

export type PriceListUpdateInput = {
  name?: string | null;
  description?: string | null;
  is_active?: boolean | null;
  store_id?: number | null;
  customer_id?: number | null;
  currency?: string | null;
  valid_from?: string | null;
  valid_until?: string | null;
};

export type PriceListItemCreateInput = {
  device_id: number;
  price: number;
  discount_percentage?: number | null;
  notes?: string | null;
};

export type PriceListItemUpdateInput = {
  price?: number | null;
  discount_percentage?: number | null;
  notes?: string | null;
};

export type PriceListListParams = {
  storeId?: number;
  customerId?: number;
  isActive?: boolean;
  includeItems?: boolean;
};

export type PriceResolutionParams = {
  deviceId: number;
  storeId?: number | null;
  customerId?: number | null;
  referenceDate?: string;
  defaultPrice?: number;
  defaultCurrency?: string;
};

export type PriceResolution = {
  device_id: number;
  price_list_id: number | null;
  price_list_name?: string | null;
  priority: number;
  scope: string;
  base_price?: number;
  discount_percentage?: number | null;
  final_price: number;
  currency: string;
};

export function listPriceLists(
  token: string,
  params: PriceListListParams = {},
  reason?: string,
): Promise<PriceList[]> {
  const searchParams = new URLSearchParams();
  if (typeof params.storeId === "number") {
    searchParams.set("store_id", String(params.storeId));
  }
  if (typeof params.customerId === "number") {
    searchParams.set("customer_id", String(params.customerId));
  }
  if (typeof params.isActive === "boolean") {
    searchParams.set("is_active", String(params.isActive));
  }
  if (typeof params.includeItems === "boolean") {
    searchParams.set("include_items", String(params.includeItems));
  }
  const query = searchParams.toString();
  const headers: Record<string, string> = {};
  if (reason) {
    headers["X-Reason"] = reason;
  }
  return requestCollection<PriceList>(
    `/price-lists${query ? `?${query}` : ""}`,
    { method: "GET", headers },
    token,
  );
}

export function getPriceList(
  token: string,
  priceListId: number,
  options: { includeItems?: boolean } = {},
  reason?: string,
): Promise<PriceList> {
  const params = new URLSearchParams();
  if (typeof options.includeItems === "boolean") {
    params.set("include_items", String(options.includeItems));
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const headers: Record<string, string> = {};
  if (reason) {
    headers["X-Reason"] = reason;
  }
  return request<PriceList>(
    `/price-lists/${priceListId}${suffix}`,
    { method: "GET", headers },
    token,
  );
}

export function createPriceList(
  token: string,
  payload: PriceListCreateInput,
  reason: string,
): Promise<PriceList> {
  return request<PriceList>(
    "/price-lists",
    {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Reason": reason },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function updatePriceList(
  token: string,
  priceListId: number,
  payload: PriceListUpdateInput,
  reason: string,
): Promise<PriceList> {
  return request<PriceList>(
    `/price-lists/${priceListId}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json", "X-Reason": reason },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function deletePriceList(
  token: string,
  priceListId: number,
  reason: string,
): Promise<void> {
  return request<void>(
    `/price-lists/${priceListId}`,
    {
      method: "DELETE",
      headers: { "X-Reason": reason },
    },
    token,
  );
}

export function createPriceListItem(
  token: string,
  priceListId: number,
  payload: PriceListItemCreateInput,
  reason: string,
): Promise<PriceListItem> {
  return request<PriceListItem>(
    `/price-lists/${priceListId}/items`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Reason": reason },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function updatePriceListItem(
  token: string,
  itemId: number,
  payload: PriceListItemUpdateInput,
  reason: string,
): Promise<PriceListItem> {
  return request<PriceListItem>(
    `/price-lists/items/${itemId}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json", "X-Reason": reason },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function deletePriceListItem(
  token: string,
  itemId: number,
  reason: string,
): Promise<void> {
  return request<void>(
    `/price-lists/items/${itemId}`,
    {
      method: "DELETE",
      headers: { "X-Reason": reason },
    },
    token,
  );
}

export function getPriceListItem(
  token: string,
  itemId: number,
  reason?: string,
): Promise<PriceListItem> {
  const headers: Record<string, string> = {};
  if (reason) {
    headers["X-Reason"] = reason;
  }
  return request<PriceListItem>(
    `/price-lists/items/${itemId}`,
    { method: "GET", headers },
    token,
  );
}

export function resolveDevicePrice(
  token: string,
  params: PriceResolutionParams,
  reason?: string,
): Promise<PriceResolution | null> {
  const searchParams = new URLSearchParams({
    device_id: String(params.deviceId),
  });
  if (typeof params.storeId === "number" && params.storeId > 0) {
    searchParams.set("store_id", String(params.storeId));
  }
  if (typeof params.customerId === "number" && params.customerId > 0) {
    searchParams.set("customer_id", String(params.customerId));
  }
  if (params.referenceDate) {
    searchParams.set("reference_date", params.referenceDate);
  }
  if (typeof params.defaultPrice === "number") {
    searchParams.set("default_price", String(params.defaultPrice));
  }
  if (params.defaultCurrency) {
    searchParams.set("default_currency", params.defaultCurrency);
  }
  const headers: Record<string, string> = {};
  if (reason) {
    headers["X-Reason"] = reason;
  }
  return request<PriceResolution | null>(
    `/price-lists/resolve?${searchParams.toString()}`,
    { method: "GET", headers },
    token,
  );
}
