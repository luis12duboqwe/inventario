import { InventoryValueFilters } from "../inventoryTypes";

export function appendNumericList(params: URLSearchParams, key: string, values?: number[]): void {
  if (!values) {
    return;
  }
  for (const value of values) {
    params.append(key, String(value));
  }
}

export function appendStringList(params: URLSearchParams, key: string, values?: string[]): void {
  if (!values) {
    return;
  }
  for (const value of values) {
    if (value) {
      params.append(key, value);
    }
  }
}

export function buildInventoryValueParams(filters: InventoryValueFilters = {}): URLSearchParams {
  const params = new URLSearchParams();
  appendNumericList(params, "store_ids", filters.storeIds);
  appendStringList(params, "categories", filters.categories);
  return params;
}

