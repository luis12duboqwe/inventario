import { request } from "../client";
import { triggerDownload } from "../client";
import {
  InventoryMovement,
  MovementInput,
  InventoryMovementsFilters,
  InventoryMovementsReport
} from "../inventoryTypes";
import { buildInventoryValueParams } from "./utils";

function buildInventoryMovementsParams(filters: InventoryMovementsFilters = {}): URLSearchParams {
  const params = buildInventoryValueParams(filters);
  if (filters.dateFrom) {
    params.append("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.append("date_to", filters.dateTo);
  }
  if (filters.movementType) {
    params.append("movement_type", filters.movementType);
  }
  return params;
}

export function getMovement(
  token: string,
  storeId: number,
  movementId: number
): Promise<InventoryMovement> {
  return request<InventoryMovement>(
    `/inventory/stores/${storeId}/movements/${movementId}`,
    { method: "GET" },
    token
  );
}

export function registerMovement(
  token: string,
  storeId: number,
  payload: MovementInput,
  comment: string
) {
  return request(`/inventory/stores/${storeId}/movements`, {
    method: "POST",
    body: JSON.stringify(payload),
    headers: { "X-Reason": comment },
  }, token);
}

export function getInventoryMovementsReport(
  token: string,
  filters: InventoryMovementsFilters = {},
): Promise<InventoryMovementsReport> {
  const params = buildInventoryMovementsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<InventoryMovementsReport>(`/reports/inventory/movements${suffix}`, { method: "GET" }, token);
}

export async function downloadInventoryMovementsCsv(
  token: string,
  reason: string,
  filters: InventoryMovementsFilters = {},
): Promise<void> {
  const params = buildInventoryMovementsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const blob = await request<Blob>(
    `/reports/inventory/movements/csv${suffix}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
  triggerDownload(blob, "movimientos_inventario.csv");
}

export async function downloadInventoryMovementsPdf(
  token: string,
  reason: string,
  filters: InventoryMovementsFilters = {},
): Promise<void> {
  const params = buildInventoryMovementsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const blob = await request<Blob>(
    `/reports/inventory/movements/pdf${suffix}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
  triggerDownload(blob, "movimientos_inventario.pdf");
}

export async function downloadInventoryMovementsXlsx(
  token: string,
  reason: string,
  filters: InventoryMovementsFilters = {},
): Promise<void> {
  const params = buildInventoryMovementsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const blob = await request<Blob>(
    `/reports/inventory/movements/xlsx${suffix}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
  triggerDownload(blob, "movimientos_inventario.xlsx");
}

export async function downloadInventoryAdjustmentsCsv(
  token: string,
  reason: string,
  filters: InventoryMovementsFilters = {},
): Promise<void> {
  const params = buildInventoryMovementsParams(filters);
  params.set("format", "csv");
  const query = params.toString();
  const blob = await request<Blob>(
    `/inventory/counts/adjustments/report?${query}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
  triggerDownload(blob, "ajustes_inventario.csv");
}

export async function downloadInventoryAdjustmentsPdf(
  token: string,
  reason: string,
  filters: InventoryMovementsFilters = {},
): Promise<void> {
  const params = buildInventoryMovementsParams(filters);
  params.set("format", "pdf");
  const query = params.toString();
  const blob = await request<Blob>(
    `/inventory/counts/adjustments/report?${query}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
  triggerDownload(blob, "ajustes_inventario.pdf");
}
