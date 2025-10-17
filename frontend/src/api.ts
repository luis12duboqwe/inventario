export type Credentials = {
  username: string;
  password: string;
  otp?: string;
};

export type Store = {
  id: number;
  name: string;
  location?: string | null;
  timezone: string;
};

export type Device = {
  id: number;
  sku: string;
  name: string;
  quantity: number;
  store_id: number;
  unit_price: number;
  inventory_value: number;
  imei?: string | null;
  serial?: string | null;
  marca?: string | null;
  modelo?: string | null;
  color?: string | null;
  capacidad_gb?: number | null;
  estado_comercial?: "nuevo" | "A" | "B" | "C";
  proveedor?: string | null;
  costo_unitario?: number;
  margen_porcentaje?: number;
  garantia_meses?: number;
  lote?: string | null;
  fecha_compra?: string | null;
};

export type CatalogDevice = Device & { store_name: string };

export type DeviceSearchFilters = {
  imei?: string;
  serial?: string;
  capacidad_gb?: number;
  color?: string;
  marca?: string;
  modelo?: string;
};

export type MovementInput = {
  device_id: number;
  movement_type: "entrada" | "salida" | "ajuste";
  quantity: number;
  reason?: string;
};

export type Summary = {
  store_id: number;
  store_name: string;
  total_items: number;
  total_value: number;
  devices: Device[];
};

export type StoreMembership = {
  id: number;
  user_id: number;
  store_id: number;
  can_create_transfer: boolean;
  can_receive_transfer: boolean;
  created_at: string;
};

export type StoreMembershipInput = {
  user_id: number;
  store_id: number;
  can_create_transfer: boolean;
  can_receive_transfer: boolean;
};

export type TransferOrderItem = {
  id: number;
  transfer_order_id: number;
  device_id: number;
  quantity: number;
};

export type TransferOrder = {
  id: number;
  origin_store_id: number;
  destination_store_id: number;
  status: "SOLICITADA" | "EN_TRANSITO" | "RECIBIDA" | "CANCELADA";
  reason?: string | null;
  created_at: string;
  updated_at: string;
  dispatched_at?: string | null;
  received_at?: string | null;
  cancelled_at?: string | null;
  items: TransferOrderItem[];
};

export type TransferOrderInput = {
  origin_store_id: number;
  destination_store_id: number;
  reason?: string;
  items: { device_id: number; quantity: number }[];
};

export type TransferTransitionInput = {
  reason?: string;
};

export type StoreValueMetric = {
  store_id: number;
  store_name: string;
  device_count: number;
  total_units: number;
  total_value: number;
};

export type LowStockDevice = {
  store_id: number;
  store_name: string;
  device_id: number;
  sku: string;
  name: string;
  quantity: number;
  unit_price: number;
  inventory_value: number;
};

export type InventoryMetrics = {
  totals: {
    stores: number;
    devices: number;
    total_units: number;
    total_value: number;
  };
  top_stores: StoreValueMetric[];
  low_stock_devices: LowStockDevice[];
};

export type AuditLogEntry = {
  id: number;
  action: string;
  entity_type: string;
  entity_id: string;
  details?: string | null;
  performed_by_id?: number | null;
  created_at: string;
};

export type RotationMetric = {
  store_id: number;
  store_name: string;
  device_id: number;
  sku: string;
  name: string;
  sold_units: number;
  received_units: number;
  rotation_rate: number;
};

export type AnalyticsRotation = {
  items: RotationMetric[];
};

export type AgingMetric = {
  device_id: number;
  sku: string;
  name: string;
  store_name: string;
  days_in_stock: number;
  quantity: number;
};

export type AnalyticsAging = {
  items: AgingMetric[];
};

export type StockoutForecastMetric = {
  device_id: number;
  sku: string;
  name: string;
  store_name: string;
  average_daily_sales: number;
  projected_days: number | null;
  quantity: number;
};

export type AnalyticsForecast = {
  items: StockoutForecastMetric[];
};

export type TOTPStatus = {
  is_active: boolean;
  activated_at?: string | null;
  last_verified_at?: string | null;
};

export type TOTPSetup = {
  secret: string;
  otpauth_url: string;
};

export type ActiveSession = {
  id: number;
  user_id: number;
  session_token: string;
  created_at: string;
  last_used_at?: string | null;
  revoked_at?: string | null;
  revoked_by_id?: number | null;
  revoke_reason?: string | null;
};

export type SessionRevokeInput = {
  reason: string;
};

export type SyncOutboxStatus = "PENDING" | "SENT" | "FAILED";

export type SyncOutboxEntry = {
  id: number;
  entity_type: string;
  entity_id: string;
  operation: string;
  payload: Record<string, unknown>;
  attempt_count: number;
  last_attempt_at?: string | null;
  status: SyncOutboxStatus;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
};

export type BackupJob = {
  id: number;
  mode: "automatico" | "manual";
  executed_at: string;
  pdf_path: string;
  archive_path: string;
  total_size_bytes: number;
  notes?: string | null;
};

export type ReleaseInfo = {
  version: string;
  release_date: string;
  notes: string;
  download_url: string;
};

export type UpdateStatus = {
  current_version: string;
  latest_version: string | null;
  is_update_available: boolean;
  latest_release: ReleaseInfo | null;
};

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", headers.get("Content-Type") ?? "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Error ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as unknown as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }

  return (await response.blob()) as unknown as T;
}

export async function login(credentials: Credentials): Promise<{ access_token: string }> {
  const params = new URLSearchParams();
  params.append("username", credentials.username);
  params.append("password", credentials.password);
  if (credentials.otp) {
    params.append("otp", credentials.otp);
  }

  const response = await fetch(`${API_URL}/auth/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: params,
  });

  if (!response.ok) {
    throw new Error("Credenciales inválidas");
  }

  return (await response.json()) as { access_token: string };
}

export function getStores(token: string): Promise<Store[]> {
  return request<Store[]>("/stores", { method: "GET" }, token);
}

export function getSummary(token: string): Promise<Summary[]> {
  return request<Summary[]>("/inventory/summary", { method: "GET" }, token);
}

export function getDevices(token: string, storeId: number): Promise<Device[]> {
  return request<Device[]>(`/stores/${storeId}/devices`, { method: "GET" }, token);
}

export function searchCatalogDevices(
  token: string,
  filters: DeviceSearchFilters
): Promise<CatalogDevice[]> {
  const params = new URLSearchParams();
  if (filters.imei) params.append("imei", filters.imei);
  if (filters.serial) params.append("serial", filters.serial);
  if (typeof filters.capacidad_gb === "number") params.append("capacidad_gb", String(filters.capacidad_gb));
  if (filters.color) params.append("color", filters.color);
  if (filters.marca) params.append("marca", filters.marca);
  if (filters.modelo) params.append("modelo", filters.modelo);
  const query = params.toString();
  const path = query ? `/inventory/devices/search?${query}` : "/inventory/devices/search";
  return request<CatalogDevice[]>(path, { method: "GET" }, token);
}

export function registerMovement(token: string, storeId: number, payload: MovementInput) {
  return request(`/inventory/stores/${storeId}/movements`, {
    method: "POST",
    body: JSON.stringify(payload),
  }, token);
}

export function listStoreMemberships(token: string, storeId: number): Promise<StoreMembership[]> {
  return request(`/stores/${storeId}/memberships`, { method: "GET" }, token);
}

export function upsertStoreMembership(
  token: string,
  storeId: number,
  userId: number,
  payload: StoreMembershipInput
): Promise<StoreMembership> {
  return request(`/stores/${storeId}/memberships/${userId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  }, token);
}

export function listTransfers(token: string, storeId?: number): Promise<TransferOrder[]> {
  const query = typeof storeId === "number" ? `?store_id=${storeId}` : "";
  const path = query ? `/transfers/${query}` : "/transfers";
  return request(path, { method: "GET" }, token);
}

export function createTransferOrder(
  token: string,
  payload: TransferOrderInput
): Promise<TransferOrder> {
  return request("/transfers", { method: "POST", body: JSON.stringify(payload) }, token);
}

export function dispatchTransferOrder(
  token: string,
  transferId: number,
  payload: TransferTransitionInput
): Promise<TransferOrder> {
  return request(`/transfers/${transferId}/dispatch`, {
    method: "POST",
    body: JSON.stringify(payload),
  }, token);
}

export function receiveTransferOrder(
  token: string,
  transferId: number,
  payload: TransferTransitionInput
): Promise<TransferOrder> {
  return request(`/transfers/${transferId}/receive`, {
    method: "POST",
    body: JSON.stringify(payload),
  }, token);
}

export function cancelTransferOrder(
  token: string,
  transferId: number,
  payload: TransferTransitionInput
): Promise<TransferOrder> {
  return request(`/transfers/${transferId}/cancel`, {
    method: "POST",
    body: JSON.stringify(payload),
  }, token);
}

export function triggerSync(token: string, storeId?: number) {
  return request(`/sync/run`, {
    method: "POST",
    body: JSON.stringify({ store_id: storeId ?? null }),
  }, token);
}

export function runBackup(token: string, note?: string): Promise<BackupJob> {
  return request<BackupJob>("/backups/run", {
    method: "POST",
    body: JSON.stringify({ nota: note }),
  }, token);
}

export function fetchBackupHistory(token: string): Promise<BackupJob[]> {
  return request<BackupJob[]>("/backups/history", { method: "GET" }, token);
}

export async function downloadInventoryPdf(token: string): Promise<void> {
  const response = await fetch(`${API_URL}/reports/inventory/pdf`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible descargar el PDF");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_inventario.pdf";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function getUpdateStatus(token: string): Promise<UpdateStatus> {
  return request<UpdateStatus>("/updates/status", { method: "GET" }, token);
}

export function getReleaseHistory(token: string, limit = 10): Promise<ReleaseInfo[]> {
  return request<ReleaseInfo[]>(`/updates/history?limit=${limit}`, { method: "GET" }, token);
}

export function getInventoryMetrics(token: string, lowStockThreshold = 5): Promise<InventoryMetrics> {
  return request<InventoryMetrics>(
    `/reports/metrics?low_stock_threshold=${lowStockThreshold}`,
    { method: "GET" },
    token
  );
}

export function getRotationAnalytics(token: string): Promise<AnalyticsRotation> {
  return request<AnalyticsRotation>("/reports/analytics/rotation", { method: "GET" }, token);
}

export function getAgingAnalytics(token: string): Promise<AnalyticsAging> {
  return request<AnalyticsAging>("/reports/analytics/aging", { method: "GET" }, token);
}

export function getForecastAnalytics(token: string): Promise<AnalyticsForecast> {
  return request<AnalyticsForecast>("/reports/analytics/stockout_forecast", { method: "GET" }, token);
}

export async function downloadAnalyticsPdf(token: string): Promise<void> {
  const response = await fetch(`${API_URL}/reports/analytics/pdf`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible descargar el PDF analítico");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_analytics.pdf";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function getTotpStatus(token: string): Promise<TOTPStatus> {
  return request<TOTPStatus>("/security/2fa/status", { method: "GET" }, token);
}

export function setupTotp(token: string): Promise<TOTPSetup> {
  return request<TOTPSetup>("/security/2fa/setup", { method: "POST" }, token);
}

export function activateTotp(token: string, code: string): Promise<TOTPStatus> {
  return request<TOTPStatus>(
    "/security/2fa/activate",
    { method: "POST", body: JSON.stringify({ code }) },
    token
  );
}

export function disableTotp(token: string): Promise<void> {
  return request<void>("/security/2fa/disable", { method: "POST" }, token);
}

export function listActiveSessions(token: string, userId?: number): Promise<ActiveSession[]> {
  const query = userId ? `?user_id=${userId}` : "";
  return request<ActiveSession[]>(`/security/sessions${query}`, { method: "GET" }, token);
}

export function revokeSession(token: string, sessionId: number, reason: string): Promise<ActiveSession> {
  return request<ActiveSession>(
    `/security/sessions/${sessionId}/revoke`,
    {
      method: "POST",
      body: JSON.stringify({ reason }),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function listSyncOutbox(token: string, statusFilter?: SyncOutboxStatus): Promise<SyncOutboxEntry[]> {
  const query = statusFilter ? `?status_filter=${statusFilter}` : "";
  return request<SyncOutboxEntry[]>(`/sync/outbox${query}`, { method: "GET" }, token);
}

export function retrySyncOutbox(token: string, ids: number[], reason: string): Promise<SyncOutboxEntry[]> {
  return request<SyncOutboxEntry[]>(
    "/sync/outbox/retry",
    {
      method: "POST",
      body: JSON.stringify({ ids }),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function getAuditLogs(token: string, limit = 100, action?: string): Promise<AuditLogEntry[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (action) {
    params.append("action", action);
  }
  return request<AuditLogEntry[]>(`/audit/logs?${params.toString()}`, { method: "GET" }, token);
}
