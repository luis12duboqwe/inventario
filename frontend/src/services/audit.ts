// [PACK26-AUDIT-SVC-START]
import { httpPost } from "./http";
import { apiMap } from "./sales"; // reutiliza base/API ya definida

type AuditEvent = {
  ts: number;              // timestamp ms
  userId?: string | null;  // opcional
  module: "POS" | "QUOTES" | "RETURNS" | "CUSTOMERS" | "CASH" | "OTHER";
  action: string;          // ej: "checkout", "discount.apply"
  entityId?: string;       // ej: saleId, quoteId
  meta?: Record<string, any>;
};

const KEY = "sm_ui_audit_queue";

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
  const payload = { items: q };
  // Endpoint asumido; ajusta si tu backend usa otro:
  const url = apiMap.audit?.bulk ?? "/api/audit/ui/bulk"; // TODO(api) si no existe
  try {
    await httpPost(url, payload, { timeoutMs: 4500 });
    writeQ([]);
    return { flushed: q.length, pending: 0 };
  } catch {
    return { flushed: 0, pending: q.length };
  }
}
// [PACK26-AUDIT-SVC-END]
