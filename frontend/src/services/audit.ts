// [PACK26-AUDIT-SVC-START]
import { http, httpGet, httpPost } from "./http";
import { apiMap } from "./sales"; // reutiliza base/API ya definida

type AuditEvent = {
  ts: number | string;     // timestamp ms o ISO8601
  userId?: string | null;  // opcional
  module: "POS" | "QUOTES" | "RETURNS" | "CUSTOMERS" | "CASH" | "OTHER";
  action: string;          // ej: "checkout", "discount.apply"
  entityId?: string;       // ej: saleId, quoteId
  meta?: Record<string, any>;
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
  try { await flushAudit(); } catch {}
}

export async function flushAudit(){
  const q = readQ();
  if (!q.length) return { flushed:0, pending:0 };
  // Evita intento de envío sin token para no provocar 401 en login
  const token = localStorage.getItem("access_token");
  if (!token) return { flushed: 0, pending: q.length };
  const payload = {
    items: q.map((item) => ({
      ...item,
      // // [PACK32-33-FE] Normaliza timestamps a ISO para FastAPI
      ts: typeof item.ts === "number" ? new Date(item.ts).toISOString() : item.ts,
    })),
  };
  const url = apiMap.audit?.bulk ?? "/api/audit/ui/bulk";
  try {
    await httpPost(url, payload, { timeoutMs: 4500, withAuth: true });
    writeQ([]);
    return { flushed: q.length, pending: 0 };
  } catch {
    return { flushed: 0, pending: q.length };
  }
}

// // [PACK32-33-FE] Consulta eventos desde el backend real.
export async function fetchAuditEvents(filters: AuditListFilters = {}): Promise<AuditListResponse>{
  const url = apiMap.audit?.list ?? "/api/audit/ui";
  const response = await httpGet<AuditListResponse>(url, { query: filters, timeoutMs: 6000 });
  const items = (response.items || []).map((item: any) => ({
    ...item,
    userId: item.userId ?? item.user_id ?? item.usuario ?? item.user,
    entityId: item.entityId ?? item.entity_id,
  }));
  return { ...response, items };
}

export async function downloadAuditExport(
  format: "csv" | "json",
  filters: AuditListFilters = {},
): Promise<{ filename: string; blob: Blob }>{
  const url = apiMap.audit?.export ?? "/api/audit/ui/export";
  const query = { ...filters, format };
  const accept = format === "csv" ? "text/csv" : "application/json";
  const payload = await http(url, { method: "GET", query, headers: { Accept: accept }, timeoutMs: 10000 });
  if (format === "csv"){
    const textPayload = String(payload ?? "");
    return {
      filename: `audit-ui.${format}`,
      blob: new Blob([textPayload], { type: "text/csv;charset=utf-8" }),
    };
  }
  const jsonPayload = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
  return {
    filename: `audit-ui.${format}`,
    blob: new Blob([jsonPayload], { type: "application/json;charset=utf-8" }),
  };
}
// [PACK26-AUDIT-SVC-END]
