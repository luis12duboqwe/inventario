import { request, requestCollection } from "../client";
import {
  ProductVariant,
  ProductVariantCreateInput,
  ProductVariantUpdateInput
} from "../inventoryTypes";

export function getProductVariants(
  token: string,
  params: { storeId?: number; deviceId?: number; includeInactive?: boolean } = {},
): Promise<ProductVariant[]> {
  const queryParams = new URLSearchParams();
  if (typeof params.storeId === "number") {
    queryParams.set("store_id", String(params.storeId));
  }
  if (typeof params.deviceId === "number") {
    queryParams.set("device_id", String(params.deviceId));
  }
  if (params.includeInactive) {
    queryParams.set("include_inactive", "true");
  }
  const suffix = queryParams.toString() ? `?${queryParams.toString()}` : "";
  return requestCollection<ProductVariant>(
    `/inventory/variants${suffix}`,
    { method: "GET" },
    token,
  );
}

export function createProductVariant(
  token: string,
  deviceId: number,
  payload: ProductVariantCreateInput,
  reason: string,
): Promise<ProductVariant> {
  return request<ProductVariant>(
    `/inventory/devices/${deviceId}/variants`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Reason": reason },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function updateProductVariant(
  token: string,
  variantId: number,
  payload: ProductVariantUpdateInput,
  reason: string,
): Promise<ProductVariant> {
  return request<ProductVariant>(
    `/inventory/variants/${variantId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "X-Reason": reason },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function archiveProductVariant(
  token: string,
  variantId: number,
  reason: string,
): Promise<ProductVariant> {
  return request<ProductVariant>(
    `/inventory/variants/${variantId}`,
    {
      method: "DELETE",
      headers: { "X-Reason": reason },
    },
    token,
  );
}
