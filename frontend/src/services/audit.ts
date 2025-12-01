import { httpClient, getAuthToken } from "@api/http";
import { apiMap } from "./sales";

type AuditEvent = {
  ts: number | string;
  userId?: string | null;
  module: "POS" | "QUOTES" | "RETURNS" | "CUSTOMERS" | "CASH" | "OTHER" | "MONITORING";
  action: string;
  entityId?: string;
  meta?: Record<string, unknown>;
};

const KEY = "sm_ui_audit_queue";

type AuditListFilters = {
  from?: string;
  to?: string;
  userId?: string;
  module?: string;
  limit?: number;
  offset?: number;
};

export type AuditListResponse = {
  items: AuditEvent[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
};

function readQ(): AuditEvent[] { try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; } }
function writeQ(q: AuditEvent[]) { localStorage.setItem(KEY, JSON.stringify(q)); }

export async function logUI(evt: AuditEvent){
  const q = readQ();
  q.push(evt);
  writeQ(q);
  try {
    await flushAudit();
  } catch (error) {
    console.error("Failed to flush audit log:", error);
  }
}

export async function flushAudit(){
  const q = readQ();
  if (!q.length) return { flushed:0, pending:0 };

  const token = getAuthToken();
  if (!token) return { flushed: 0, pending: q.length };

  const payload = {
    items: q.map((item) => ({
      ...item,
      ts: typeof item.ts === "number" ? new Date(item.ts).toISOString() : item.ts,
    })),
  };
  const url = apiMap.audit?.bulk ?? "/api/audit/ui/bulk";
  try {
    await httpClient.post(url, payload, { timeout: 4500 });
    writeQ([]);
    return { flushed: q.length, pending: 0 };
  } catch {
    return { flushed: 0, pending: q.length };
  }
}

export async function fetchAuditEvents(filters: AuditListFilters = {}): Promise<AuditListResponse>{
  const url = apiMap.audit?.list ?? "/api/audit/ui";
  const response = await httpClient.get<AuditListResponse>(url, { params: filters, timeout: 6000 });
  const data = response.data;
  const items = (data.items || []).map((item: Record<string, unknown>) => ({
    ...item,
    userId: item.userId ?? item.user_id ?? item.usuario ?? item.user,
    entityId: item.entityId ?? item.entity_id,
  })) as unknown as AuditEvent[];
  return { ...data, items };
}

export async function downloadAuditExport(
  format: "csv" | "json",
  filters: AuditListFilters = {},
): Promise<{ filename: string; blob: Blob }>{
  const url = apiMap.audit?.export ?? "/api/audit/ui/export";
  const params = { ...filters, format };
  const accept = format === "csv" ? "text/csv" : "application/json";

  const response = await httpClient.get(url, {
      params,
      headers: { Accept: accept },
      timeout: 10000,
      responseType: format === "csv" ? 'blob' : 'json'
  });

  let blob: Blob;
  if (format === "csv") {
      blob = response.data as Blob;
  } else {
      const jsonPayload = JSON.stringify(response.data, null, 2);
      blob = new Blob([jsonPayload], { type: "application/json;charset=utf-8" });
  }

  return {
    filename: `audit-ui.${format}`,
    blob: blob,
  };
}
