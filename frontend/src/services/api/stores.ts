import httpClient from "./http";
import type { Device, Store } from "../../api";

export async function fetchStores(): Promise<Store[]> {
  const response = await httpClient.get<Store[]>("/stores");
  return response.data;
}

export async function fetchStoreDevices(
  storeId: number,
  options: { includeIdentifier?: boolean; signal?: AbortSignal } = {},
): Promise<Device[]> {
  const params = new URLSearchParams();
  if (options.includeIdentifier) {
    params.set("include_identifier", "true");
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";
  const response = await httpClient.get<Device[]>(`/stores/${storeId}/devices${suffix}`);
  return response.data;
}

export type { Store } from "../../api";
