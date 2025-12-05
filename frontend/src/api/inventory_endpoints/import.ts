import { request, requestCollection } from "../client";
import {
  InventorySmartImportResponse,
  InventoryImportHistoryEntry,
  ImportValidationSummary,
  ImportValidationDetail,
  ImportValidation
} from "../inventoryTypes";

export function smartInventoryImport(
  token: string,
  file: File,
  reason: string,
  options: { overrides?: Record<string, string> } = {},
): Promise<InventorySmartImportResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (options.overrides && Object.keys(options.overrides).length > 0) {
    formData.append("overrides", JSON.stringify(options.overrides));
  }
  return request<InventorySmartImportResponse>(
    "/inventory/import/smart",
    { method: "POST", body: formData, headers: { "X-Reason": reason } },
    token,
  );
}

export function getSmartImportHistory(
  token: string,
  limit = 10,
): Promise<InventoryImportHistoryEntry[]> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  return requestCollection<InventoryImportHistoryEntry>(
    `/inventory/import/smart/history?${params.toString()}`,
    { method: "GET" },
    token,
  );
}

export function getImportValidationReport(token: string): Promise<ImportValidationSummary> {
  return request<ImportValidationSummary>("/validacion/reporte", { method: "GET" }, token);
}

export function getPendingImportValidations(
  token: string,
  limit = 200,
): Promise<ImportValidationDetail[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  return requestCollection<ImportValidationDetail>(
    `/validacion/pendientes?${params.toString()}`,
    { method: "GET" },
    token,
  );
}

export function markImportValidationCorrected(
  token: string,
  validationId: number,
  reason: string,
): Promise<ImportValidation> {
  return request<ImportValidation>(
    `/validacion/${validationId}/corregir`,
    { method: "PATCH", headers: { "X-Reason": reason } },
    token,
  );
}
