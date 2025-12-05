import { request, requestCollection, API_URL } from "./client";
import { SystemLogLevel } from "./types";
import { GlobalReportAlert, GlobalReportLogEntry, GlobalReportErrorEntry } from "./reports";

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
  priority: "HIGH" | "NORMAL" | "LOW";
  error_message?: string | null;
  conflict_flag: boolean;
  version: number;
  created_at: string;
  updated_at: string;
  latency_ms?: number | null;
  processing_latency_ms?: number | null;
  status_detail?: string | null;
};

export type SyncOutboxStatsEntry = {
  entity_type: string;
  priority: "HIGH" | "NORMAL" | "LOW";
  total: number;
  pending: number;
  failed: number;
  conflicts: number;
  latest_update?: string | null;
  oldest_pending?: string | null;
  oldest_pending_seconds?: number | null;
  last_conflict_at?: string | null;
};

export type SyncQueueStatus = "PENDING" | "SENT" | "FAILED";

export type SyncQueueEntry = {
  id: number;
  event_type: string;
  payload: Record<string, unknown>;
  idempotency_key: string | null;
  status: SyncQueueStatus;
  attempts: number;
  last_error: string | null;
  created_at: string;
  updated_at: string;
};

export type SyncQueueSummary = {
  percent: number;
  total: number;
  processed: number;
  pending: number;
  failed: number;
  last_updated: string | null;
  oldest_pending: string | null;
};

export type SyncHybridComponent = {
  total: number;
  processed: number;
  pending: number;
  failed: number;
  latest_update: string | null;
  oldest_pending: string | null;
};

export type SyncHybridProgress = {
  percent: number;
  total: number;
  processed: number;
  pending: number;
  failed: number;
  components: {
    queue: SyncHybridComponent;
    outbox: SyncHybridComponent;
  };
};

export type SyncHybridForecast = {
  lookback_minutes: number;
  processed_recent: number;
  processed_queue: number;
  processed_outbox: number;
  attempts_total: number;
  attempts_successful: number;
  success_rate: number;
  events_per_minute: number;
  backlog_pending: number;
  backlog_failed: number;
  backlog_total: number;
  estimated_minutes_remaining: number | null;
  estimated_completion: string | null;
  generated_at: string;
  progress: SyncHybridProgress;
};

export type SyncHybridModuleBreakdownComponent = {
  total: number;
  processed: number;
  pending: number;
  failed: number;
};

export type SyncHybridModuleBreakdownItem = {
  module: string;
  label: string;
  total: number;
  processed: number;
  pending: number;
  failed: number;
  percent: number;
  queue: SyncHybridModuleBreakdownComponent;
  outbox: SyncHybridModuleBreakdownComponent;
};

export type SyncHybridRemainingBreakdown = {
  total: number;
  pending: number;
  failed: number;
  remote_pending: number;
  remote_failed: number;
  outbox_pending: number;
  outbox_failed: number;
  estimated_minutes_remaining: number | null;
  estimated_completion: string | null;
};

export type SyncHybridOverview = {
  generated_at: string;
  percent: number;
  total: number;
  processed: number;
  pending: number;
  failed: number;
  remaining: SyncHybridRemainingBreakdown;
  queue_summary: SyncQueueSummary | null;
  progress: SyncHybridProgress;
  forecast: SyncHybridForecast;
  breakdown: SyncHybridModuleBreakdownItem[];
};

export type SyncSessionCompact = {
  id: number;
  mode: string;
  status: string;
  started_at: string;
  finished_at?: string | null;
  error_message?: string | null;
};

export type SyncStoreHistory = {
  store_id: number | null;
  store_name: string;
  sessions: SyncSessionCompact[];
};

export type SyncBranchOverview = {
  store_id: number;
  store_name: string;
  store_code: string;
  timezone: string;
  inventory_value: number;
  last_sync_at?: string | null;
  last_sync_mode?: string | null;
  last_sync_status?: string | null;
  pending_inbound: number;
  pending_outbound: number;
  version: string;
};

export type SyncConflictLog = {
  id: number;
  store_id: number;
  store_name: string;
  entity_type: string;
  entity_id: string;
  conflict_type: string;
  server_data: Record<string, unknown>;
  client_data: Record<string, unknown>;
  resolution?: string | null;
  resolved_at?: string | null;
  created_at: string;
};

export type SyncConflictFilters = {
  store_id?: number;
  date_from?: string;
  date_to?: string;
  severity?: string;
  limit?: number;
};

export type ObservabilityLatencySample = {
  entity_type: string;
  pending: number;
  failed: number;
  oldest_pending_seconds: number | null;
  latest_update: string | null;
};

export type ObservabilityLatencySummary = {
  average_seconds: number | null;
  percentile_95_seconds: number | null;
  max_seconds: number | null;
  samples: ObservabilityLatencySample[];
};

export type ObservabilityErrorSummary = {
  total_logs: number;
  total_errors: number;
  info: number;
  warning: number;
  error: number;
  critical: number;
  latest_error_at: string | null;
};

export type ObservabilitySyncSummary = {
  outbox_stats: SyncOutboxStatsEntry[];
  total_pending: number;
  total_failed: number;
  hybrid_progress: SyncHybridProgress | null;
};

export type ObservabilityNotification = {
  id: string;
  title: string;
  message: string;
  severity: SystemLogLevel;
  occurred_at: string | null;
  reference: string | null;
};

export type ObservabilitySnapshot = {
  generated_at: string;
  latency: ObservabilityLatencySummary;
  errors: ObservabilityErrorSummary;
  sync: ObservabilitySyncSummary;
  logs: GlobalReportLogEntry[];
  system_errors: GlobalReportErrorEntry[];
  alerts: GlobalReportAlert[];
  notifications: ObservabilityNotification[];
};

export type SyncQueueEventInput = {
  event_type: string;
  payload: Record<string, unknown>;
  idempotency_key?: string | null;
};

export type SyncQueueEnqueueResponse = {
  queued: SyncQueueEntry[];
  reused: SyncQueueEntry[];
};

export type SyncQueueDispatchResult = {
  processed: number;
  sent: number;
  failed: number;
  retried: number;
};

export function enqueueSyncQueueEvents(
  token: string,
  events: SyncQueueEventInput[],
): Promise<SyncQueueEnqueueResponse> {
  return request(`/sync/events`, { method: "POST", body: JSON.stringify({ events }) }, token);
}

export function dispatchSyncQueueEvents(
  token: string,
  limit = 25,
): Promise<SyncQueueDispatchResult> {
  const params = new URLSearchParams({ limit: String(limit) });
  return request(`/sync/dispatch?${params.toString()}`, { method: "POST" }, token);
}

export function listSyncQueueStatus(
  token: string,
  params: { limit?: number; status?: SyncQueueStatus } = {},
): Promise<SyncQueueEntry[]> {
  const searchParams = new URLSearchParams();
  if (params.limit) {
    searchParams.set("limit", String(params.limit));
  }
  if (params.status) {
    searchParams.set("status", params.status);
  }
  const query = searchParams.toString();
  const suffix = query ? `?${query}` : "";
  return requestCollection<SyncQueueEntry>(`/sync/status${suffix}`, { method: "GET" }, token);
}

export function listSyncOutbox(token: string, statusFilter?: SyncOutboxStatus): Promise<SyncOutboxEntry[]> {
  const query = statusFilter ? `?status_filter=${statusFilter}` : "";
  return requestCollection<SyncOutboxEntry>(`/sync/outbox${query}`, { method: "GET" }, token);
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

export function updateSyncOutboxPriority(
  token: string,
  id: number,
  priority: "HIGH" | "NORMAL" | "LOW",
  reason: string,
): Promise<SyncOutboxEntry> {
  return request<SyncOutboxEntry>(
    `/sync/outbox/${id}/priority`,
    {
      method: "PATCH",
      body: JSON.stringify({ priority }),
      headers: { "X-Reason": reason },
    },
    token,
  );
}

export function resolveSyncOutboxConflicts(
  token: string,
  ids: number[],
  reason: string,
): Promise<SyncOutboxEntry[]> {
  return request<SyncOutboxEntry[]>(
    "/sync/outbox/resolve",
    {
      method: "POST",
      body: JSON.stringify({ ids }),
      headers: { "X-Reason": reason },
    },
    token,
  );
}

export function getSyncOutboxStats(token: string): Promise<SyncOutboxStatsEntry[]> {
  return requestCollection<SyncOutboxStatsEntry>("/sync/outbox/stats", { method: "GET" }, token);
}

export function getObservabilitySnapshot(token: string): Promise<ObservabilitySnapshot> {
  return request<ObservabilitySnapshot>("/admin/observability", { method: "GET" }, token);
}

export function getSyncQueueSummary(token: string): Promise<SyncQueueSummary> {
  return request<SyncQueueSummary>("/sync/status/summary", { method: "GET" }, token);
}

export function getSyncHybridBreakdown(
  token: string,
): Promise<SyncHybridModuleBreakdownItem[]> {
  return requestCollection<SyncHybridModuleBreakdownItem>(
    "/sync/status/breakdown",
    { method: "GET" },
    token,
  );
}

export function getSyncHybridProgress(token: string): Promise<SyncHybridProgress> {
  return request<SyncHybridProgress>("/sync/status/hybrid", { method: "GET" }, token);
}

export function getSyncHybridForecast(
  token: string,
  lookbackMinutes?: number,
): Promise<SyncHybridForecast> {
  const search = typeof lookbackMinutes === "number" ? `?lookback_minutes=${lookbackMinutes}` : "";
  return request<SyncHybridForecast>(`/sync/status/forecast${search}`, { method: "GET" }, token);
}

export function getSyncHybridOverview(token: string): Promise<SyncHybridOverview> {
  return request<SyncHybridOverview>("/sync/status/overview", { method: "GET" }, token);
}

export function getSyncHistory(token: string, limitPerStore = 5): Promise<SyncStoreHistory[]> {
  return requestCollection<SyncStoreHistory>(
    `/sync/history?limit_per_store=${limitPerStore}`,
    { method: "GET" },
    token,
  );
}

export async function downloadSyncHistoryCsv(
  token: string,
  reason: string,
  limitPerStore = 10,
): Promise<void> {
  const response = await fetch(`${API_URL}/sync/history/export?limit_per_store=${limitPerStore}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible exportar el historial de sincronización");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "historial_sincronizacion.csv";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function getSyncOverview(token: string, storeId?: number): Promise<SyncBranchOverview[]> {
  const query = typeof storeId === "number" ? `?store_id=${storeId}` : "";
  return requestCollection<SyncBranchOverview>(`/sync/overview${query}`, { method: "GET" }, token);
}

function buildSyncConflictQuery(filters: SyncConflictFilters = {}): string {
  const params = new URLSearchParams();
  if (typeof filters.store_id === "number") {
    params.set("store_id", String(filters.store_id));
  }
  if (filters.date_from) {
    params.set("date_from", filters.date_from);
  }
  if (filters.date_to) {
    params.set("date_to", filters.date_to);
  }
  if (filters.severity) {
    params.set("severity", filters.severity);
  }
  if (typeof filters.limit === "number") {
    params.set("limit", String(filters.limit));
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function listSyncConflicts(
  token: string,
  filters: SyncConflictFilters = {},
): Promise<SyncConflictLog[]> {
  const query = buildSyncConflictQuery(filters);
  return requestCollection<SyncConflictLog>(`/sync/conflicts${query}`, { method: "GET" }, token);
}

export function exportSyncConflictsPdf(
  token: string,
  reason: string,
  filters: SyncConflictFilters = {},
): Promise<Blob> {
  const query = buildSyncConflictQuery(filters);
  return request<Blob>(
    `/sync/conflicts/export/pdf${query}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
}

export function exportSyncConflictsExcel(
  token: string,
  reason: string,
  filters: SyncConflictFilters = {},
): Promise<Blob> {
  const query = buildSyncConflictQuery(filters);
  return request<Blob>(
    `/sync/conflicts/export/xlsx${query}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token,
  );
}

export function resolveSyncQueueEvent(token: string, queueId: number): Promise<SyncQueueEntry> {
  return request(`/sync/resolve/${queueId}`, { method: "POST" }, token);
}

export function triggerSync(token: string, reason: string): Promise<void> {
  return request<void>(
    "/sync/run",
    {
      method: "POST",
      body: JSON.stringify({ reason }),
      headers: { "X-Reason": reason },
    },
    token
  );
}
