import { request, requestCollection } from "./client";

export type AuditLogEntry = {
  id: number;
  action: string;
  entity_type: string;
  entity_id: string;
  details?: string | null;
  performed_by_id?: number | null;
  created_at: string;
  severity: "info" | "warning" | "critical";
  severity_label: string;
  module?: string | null;
};

export type AuditLogFilters = {
  limit?: number;
  action?: string;
  entity_type?: string;
  module?: string;
  performed_by_id?: number;
  severity?: AuditLogEntry["severity"];
  date_from?: string;
  date_to?: string;
};

export type AuditReminderEntry = {
  entity_type: string;
  entity_id: string;
  first_seen: string;
  last_seen: string;
  occurrences: number;
  latest_action: string;
  latest_details?: string | null;
  status: "pending" | "acknowledged";
  acknowledged_at?: string | null;
  acknowledged_by_id?: number | null;
  acknowledged_by_name?: string | null;
  acknowledged_note?: string | null;
};

export type AuditReminderSummary = {
  threshold_minutes: number;
  min_occurrences: number;
  total: number;
  pending_count: number;
  acknowledged_count: number;
  persistent: AuditReminderEntry[];
};

export type AuditAcknowledgementInput = {
  entity_type: string;
  entity_id: string;
  note?: string;
};

export type AuditAcknowledgementResponse = {
  entity_type: string;
  entity_id: string;
  acknowledged_at: string;
  acknowledged_by_id?: number | null;
  acknowledged_by_name?: string | null;
  note?: string | null;
};

export type AuditHighlight = {
  id: number;
  action: string;
  created_at: string;
  severity: "info" | "warning" | "critical";
  entity_type: string;
  entity_id: string;
  status: "pending" | "acknowledged";
  acknowledged_at?: string | null;
  acknowledged_by_id?: number | null;
  acknowledged_by_name?: string | null;
  acknowledged_note?: string | null;
};

export type AuditAcknowledgedEntity = {
  entity_type: string;
  entity_id: string;
  acknowledged_at: string;
  acknowledged_by_id?: number | null;
  acknowledged_by_name?: string | null;
  note?: string | null;
};

export type DashboardAuditAlerts = {
  total: number;
  critical: number;
  warning: number;
  info: number;
  has_alerts: boolean;
  pending_count: number;
  acknowledged_count: number;
  highlights: AuditHighlight[];
  acknowledged_entities: AuditAcknowledgedEntity[];
};

function buildAuditQuery(filters: AuditLogFilters): string {
  const params = new URLSearchParams();
  if (filters.limit) {
    params.set("limit", filters.limit.toString());
  }
  if (filters.action) {
    params.set("action", filters.action);
  }
  if (filters.entity_type) {
    params.set("entity_type", filters.entity_type);
  }
  if (filters.module) {
    params.set("module", filters.module);
  }
  if (filters.performed_by_id) {
    params.set("performed_by_id", filters.performed_by_id.toString());
  }
  if (filters.severity) {
    params.set("severity", filters.severity);
  }
  if (filters.date_from) {
    params.set("date_from", filters.date_from);
  }
  if (filters.date_to) {
    params.set("date_to", filters.date_to);
  }
  return params.toString();
}

export function getAuditLogs(token: string, filters: AuditLogFilters = {}): Promise<AuditLogEntry[]> {
  const query = buildAuditQuery(filters);
  const suffix = query ? `?${query}` : "";
  return requestCollection<AuditLogEntry>(`/audit/logs${suffix}`, { method: "GET" }, token);
}

export function exportAuditLogsCsv(
  token: string,
  filters: AuditLogFilters = {},
  reason = "Descarga auditoría"
): Promise<Blob> {
  const query = buildAuditQuery(filters);
  const suffix = query ? `?${query}` : "";
  return request<Blob>(
    `/audit/logs/export.csv${suffix}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token
  );
}

export function downloadAuditPdf(
  token: string,
  filters: AuditLogFilters = {},
  reason = "Reporte auditoría"
): Promise<Blob> {
  const query = buildAuditQuery(filters);
  const suffix = query ? `?${query}` : "";
  return request<Blob>(
    `/reports/audit/pdf${suffix}`,
    { method: "GET", headers: { "X-Reason": reason }, responseType: "blob" },
    token
  );
}

export function getAuditReminders(token: string): Promise<AuditReminderSummary> {
  return request<AuditReminderSummary>("/audit/reminders", { method: "GET" }, token);
}

export function acknowledgeAuditAlert(
  token: string,
  payload: AuditAcknowledgementInput,
  reason: string
): Promise<AuditAcknowledgementResponse> {
  return request<AuditAcknowledgementResponse>(
    "/audit/acknowledgements",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}
