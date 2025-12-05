import { request, requestCollection } from "../client";
import { PaginatedResponse } from "../types";
import {
  Device,
  DeviceListFilters,
  DeviceUpdateInput,
  InventorySmartImportResponse,
  DeviceSearchFilters,
  CatalogDevice,
  DeviceIdentifier,
  DeviceIdentifierInput
} from "../inventoryTypes";
import { triggerDownload } from "../client";

function buildDeviceFilterParams(filters: DeviceListFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.search) {
    params.append("search", filters.search);
  }
  if (filters.estado) {
    params.append("estado", filters.estado);
  }
  if (filters.categoria) {
    params.append("categoria", filters.categoria);
  }
  if (filters.condicion) {
    params.append("condicion", filters.condicion);
  }
  if (filters.estado_inventario) {
    params.append("estado_inventario", filters.estado_inventario);
  }
  if (filters.ubicacion) {
    params.append("ubicacion", filters.ubicacion);
  }
  if (filters.proveedor) {
    params.append("proveedor", filters.proveedor);
  }
  if (filters.warehouse_id != null) {
    params.append("warehouse_id", String(filters.warehouse_id));
  }
  if (filters.fecha_ingreso_desde) {
    params.append("fecha_ingreso_desde", filters.fecha_ingreso_desde);
  }
  if (filters.fecha_ingreso_hasta) {
    params.append("fecha_ingreso_hasta", filters.fecha_ingreso_hasta);
  }
  if (typeof filters.limit === "number") {
    params.append("limit", String(filters.limit));
  }
  return params;
}

function buildDeviceSearchFilterParams(filters: DeviceSearchFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.imei) {
    params.append("imei", filters.imei);
  }
  if (filters.serial) {
    params.append("serial", filters.serial);
  }
  if (filters.capacidad_gb !== undefined) {
    params.append("capacidad_gb", String(filters.capacidad_gb));
  }
  if (filters.color) {
    params.append("color", filters.color);
  }
  if (filters.marca) {
    params.append("marca", filters.marca);
  }
  if (filters.modelo) {
    params.append("modelo", filters.modelo);
  }
  if (filters.categoria) {
    params.append("categoria", filters.categoria);
  }
  if (filters.condicion) {
    params.append("condicion", filters.condicion);
  }
  if (filters.estado_comercial) {
    params.append("estado_comercial", filters.estado_comercial);
  }
  if (filters.estado) {
    params.append("estado", filters.estado);
  }
  if (filters.ubicacion) {
    params.append("ubicacion", filters.ubicacion);
  }
  if (filters.proveedor) {
    params.append("proveedor", filters.proveedor);
  }
  if (filters.fecha_ingreso_desde) {
    params.append("fecha_ingreso_desde", filters.fecha_ingreso_desde);
  }
  if (filters.fecha_ingreso_hasta) {
    params.append("fecha_ingreso_hasta", filters.fecha_ingreso_hasta);
  }
  return params;
}

export function getDevices(
  token: string,
  storeId: number,
  filters: DeviceListFilters = {}
): Promise<Device[]> {
  const params = buildDeviceFilterParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return requestCollection<Device>(`/stores/${storeId}/devices${suffix}`, { method: "GET" }, token);
}

export function updateDevice(
  token: string,
  storeId: number,
  deviceId: number,
  payload: DeviceUpdateInput,
  reason: string
): Promise<Device> {
  return request<Device>(
    `/inventory/stores/${storeId}/devices/${deviceId}`,
    { method: "PATCH", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token,
  );
}

export function getIncompleteDevices(
  token: string,
  storeId?: number,
  limit = 100,
): Promise<Device[]> {
  const params = new URLSearchParams();
  if (storeId != null) {
    params.set("store_id", String(storeId));
  }
  params.set("limit", String(limit));
  const query = params.toString();
  const url = query ? `/inventory/devices/incomplete?${query}` : "/inventory/devices/incomplete";
  return requestCollection<Device>(url, { method: "GET" }, token);
}

export async function exportStoreDevicesCsv(
  token: string,
  storeId: number,
  filters: DeviceListFilters,
  reason: string,
): Promise<void> {
  const params = buildDeviceFilterParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const blob = await request<Blob>(
    `/inventory/stores/${storeId}/devices/export${suffix}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
  triggerDownload(blob, `dispositivos_sucursal_${storeId}.csv`);
}

export function importStoreDevicesCsv(
  token: string,
  storeId: number,
  file: File,
  reason: string,
): Promise<InventorySmartImportResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request<InventorySmartImportResponse>(
    `/inventory/stores/${storeId}/devices/import`,
    { method: "POST", body: formData, headers: { "X-Reason": reason } },
    token,
  );
}

export async function searchCatalogDevices(
  token: string,
  filters: DeviceSearchFilters,
  limit = 20,
): Promise<CatalogDevice[]> {
  const params = buildDeviceSearchFilterParams(filters);
  params.set("limit", String(limit));
  const response = await request<PaginatedResponse<CatalogDevice>>(
    `/inventory/devices/search?${params.toString()}`,
    { method: "GET" },
    token,
  );
  return response.items;
}

export function getDeviceIdentifier(
  token: string,
  storeId: number,
  deviceId: number,
): Promise<DeviceIdentifier> {
  return request<DeviceIdentifier>(
    `/inventory/stores/${storeId}/devices/${deviceId}/identifier`,
    { method: "GET" },
    token,
  );
}

export function upsertDeviceIdentifier(
  token: string,
  storeId: number,
  deviceId: number,
  payload: DeviceIdentifierInput,
  reason: string,
): Promise<DeviceIdentifier> {
  return request<DeviceIdentifier>(
    `/inventory/stores/${storeId}/devices/${deviceId}/identifier`,
    { method: "PUT", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token,
  );
}
