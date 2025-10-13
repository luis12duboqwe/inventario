export type Credentials = {
  username: string;
  password: string;
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
  devices: Device[];
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

export function registerMovement(token: string, storeId: number, payload: MovementInput) {
  return request(`/inventory/stores/${storeId}/movements`, {
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
