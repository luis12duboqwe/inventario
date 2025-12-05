import { request, requestCollection } from "../client";
import {
  ProductBundle,
  ProductBundleCreateInput,
  ProductBundleUpdateInput
} from "../inventoryTypes";

export function getProductBundles(
  token: string,
  params: { storeId?: number; includeInactive?: boolean } = {},
): Promise<ProductBundle[]> {
  const queryParams = new URLSearchParams();
  if (typeof params.storeId === "number") {
    queryParams.set("store_id", String(params.storeId));
  }
  if (params.includeInactive) {
    queryParams.set("include_inactive", "true");
  }
  const suffix = queryParams.toString() ? `?${queryParams.toString()}` : "";
  return requestCollection<ProductBundle>(
    `/inventory/bundles${suffix}`,
    { method: "GET" },
    token,
  );
}

export function createProductBundle(
  token: string,
  payload: ProductBundleCreateInput,
  reason: string,
): Promise<ProductBundle> {
  return request<ProductBundle>(
    "/inventory/bundles",
    {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Reason": reason },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function updateProductBundle(
  token: string,
  bundleId: number,
  payload: ProductBundleUpdateInput,
  reason: string,
): Promise<ProductBundle> {
  return request<ProductBundle>(
    `/inventory/bundles/${bundleId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "X-Reason": reason },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function archiveProductBundle(
  token: string,
  bundleId: number,
  reason: string,
): Promise<ProductBundle> {
  return request<ProductBundle>(
    `/inventory/bundles/${bundleId}`,
    {
      method: "DELETE",
      headers: { "X-Reason": reason },
    },
    token,
  );
}
