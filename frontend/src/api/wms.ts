import { request, requestCollection } from "./client";
import type { Device } from "./inventory";

export type WMSBin = {
  id: number;
  codigo: string;
  sucursal_id: number;
  pasillo?: string | null;
  rack?: string | null;
  nivel?: string | null;
  descripcion?: string | null;
  fecha_creacion: string;
  fecha_actualizacion: string;
};

export type WMSBinCreatePayload = {
  codigo: string;
  pasillo?: string | null;
  rack?: string | null;
  nivel?: string | null;
  descripcion?: string | null;
};

export type WMSBinUpdatePayload = Partial<WMSBinCreatePayload>;

export type DeviceBinAssignment = {
  producto_id: number;
  bin: WMSBin;
  asignado_en: string;
  desasignado_en?: string | null;
};

export function listWMSBins(
  token: string,
  storeId: number,
  params: { limit?: number; offset?: number } = {}
): Promise<WMSBin[]> {
  const searchParams = new URLSearchParams();
  if (typeof params.limit === "number") {
    searchParams.set("limit", String(params.limit));
  }
  if (typeof params.offset === "number") {
    searchParams.set("offset", String(params.offset));
  }
  const query = searchParams.toString();
  const suffix = query ? `?${query}` : "";
  return requestCollection<WMSBin>(
    `/inventory/stores/${storeId}/bins${suffix}`,
    { method: "GET" },
    token
  );
}

export function createWMSBin(
  token: string,
  storeId: number,
  payload: WMSBinCreatePayload,
  reason: string
): Promise<WMSBin> {
  return request<WMSBin>(
    `/inventory/stores/${storeId}/bins`,
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function updateWMSBin(
  token: string,
  storeId: number,
  binId: number,
  payload: WMSBinUpdatePayload,
  reason: string
): Promise<WMSBin> {
  return request<WMSBin>(
    `/inventory/stores/${storeId}/bins/${binId}`,
    { method: "PUT", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function getDeviceBin(
  token: string,
  storeId: number,
  deviceId: number
): Promise<WMSBin | null> {
  return request<WMSBin | null>(
    `/inventory/stores/${storeId}/devices/${deviceId}/bin`,
    { method: "GET" },
    token
  );
}

export function assignDeviceBin(
  token: string,
  storeId: number,
  deviceId: number,
  binId: number,
  reason: string
): Promise<DeviceBinAssignment> {
  return request<DeviceBinAssignment>(
    `/inventory/stores/${storeId}/devices/${deviceId}/bin?bin_id=${binId}`,
    { method: "POST", headers: { "X-Reason": reason } },
    token
  );
}

export function listDevicesInBin(
  token: string,
  storeId: number,
  binId: number,
  params: { limit?: number; offset?: number } = {}
): Promise<Device[]> {
  const searchParams = new URLSearchParams();
  if (typeof params.limit === "number") {
    searchParams.set("limit", String(params.limit));
  }
  if (typeof params.offset === "number") {
    searchParams.set("offset", String(params.offset));
  }
  const query = searchParams.toString();
  const suffix = query ? `?${query}` : "";
  return requestCollection<Device>(
    `/inventory/stores/${storeId}/bins/${binId}/devices${suffix}`,
    { method: "GET" },
    token
  );
}
