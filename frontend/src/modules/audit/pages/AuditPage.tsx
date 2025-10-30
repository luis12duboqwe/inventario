// [PACK26-AUDIT-PAGE-START]
import { FormEvent, useEffect, useState } from "react";
import { downloadBlob } from "../../../lib/download";
import { useAuthz, PERMS } from "../../../auth/useAuthz";
import {
  fetchAuditEvents,
  downloadAuditExport,
  AuditListResponse,
} from "../../../services/audit";

type Row = { ts:number; userId?:string; module:string; action:string; entityId?:string; meta?:any };

export default function AuditPage(){
  const { can } = useAuthz();
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState<{ total: number; limit: number; offset: number }>({ total: 0, limit: 100, offset: 0 });
  const [filters, setFilters] = useState({ userId: "", module: "", from: "", to: "" });
  const [appliedFilters, setAppliedFilters] = useState({ userId: "", module: "", from: "", to: "" });

  useEffect(()=>{
    if (!can(PERMS.AUDIT_VIEW)) return;
    (async ()=>{
      setLoading(true);
      setError(null);
      try {
        // // [PACK32-33-FE] Prefiere backend real con filtros y paginación
        const response: AuditListResponse = await fetchAuditEvents({
          ...Object.fromEntries(
            Object.entries(appliedFilters).filter(([, value]) => value)
          ),
          limit: pagination.limit,
          offset: pagination.offset,
        });
        setRows(
          (response.items || []).map((item) => ({
            ts: typeof item.ts === "string" ? new Date(item.ts).getTime() : item.ts,
            userId: item.userId ?? undefined,
            module: item.module,
            action: item.action,
            entityId: item.entityId ?? undefined,
            meta: item.meta,
          }))
        );
        setPagination((prev) => {
          const next = { total: response.total, limit: response.limit, offset: response.offset };
          if (prev.total === next.total && prev.limit === next.limit && prev.offset === next.offset) {
            return prev;
          }
          return next;
        });
      } catch (err) {
        // fallback: mostrar cola local si no hay backend
        try {
          const local = JSON.parse(localStorage.getItem("sm_ui_audit_queue") || "[]");
          setRows(local);
          setPagination((prev) => {
            const next = { total: local.length, limit: local.length || 1, offset: 0 };
            if (prev.total === next.total && prev.limit === next.limit && prev.offset === next.offset) {
              return prev;
            }
            return next;
          });
        } catch {}
        setError((err as any)?.message ?? "No se pudo contactar la API de auditoría");
      } finally { setLoading(false); }
    })();
  }, [can, appliedFilters, pagination.limit, pagination.offset]);

  function handleFilterSubmit(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    setPagination((prev) => ({ ...prev, offset: 0 }));
    setAppliedFilters({ ...filters });
  }

  async function handleExport(format: "csv" | "json") {
    try {
      setError(null);
      const { blob, filename } = await downloadAuditExport(format, {
        ...Object.fromEntries(Object.entries(appliedFilters).filter(([, value]) => value)),
        limit: pagination.limit,
        offset: pagination.offset,
      });
      downloadBlob(blob, filename);
    } catch (err) {
      setError((err as any)?.message ?? `No se pudo exportar la bitácora (${format})`);
    }
  }

  if (!can(PERMS.AUDIT_VIEW)) return <div>No autorizado</div>;

  return (
    <div data-testid="audit-page">
      <h2>Auditoría UI</h2>
      <form onSubmit={handleFilterSubmit} style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "1rem" }}>
        <label style={{ display: "flex", flexDirection: "column" }}>
          Usuario
          <input value={filters.userId} onChange={(e)=>setFilters((prev)=>({ ...prev, userId: e.target.value }))} placeholder="userId" />
        </label>
        <label style={{ display: "flex", flexDirection: "column" }}>
          Módulo
          <input value={filters.module} onChange={(e)=>setFilters((prev)=>({ ...prev, module: e.target.value }))} placeholder="module" />
        </label>
        <label style={{ display: "flex", flexDirection: "column" }}>
          Desde
          <input type="datetime-local" value={filters.from} onChange={(e)=>setFilters((prev)=>({ ...prev, from: e.target.value }))} />
        </label>
        <label style={{ display: "flex", flexDirection: "column" }}>
          Hasta
          <input type="datetime-local" value={filters.to} onChange={(e)=>setFilters((prev)=>({ ...prev, to: e.target.value }))} />
        </label>
        <button type="submit">Aplicar filtros</button>
        <button type="button" onClick={()=>handleExport("csv")}>Exportar CSV</button>
        <button type="button" onClick={()=>handleExport("json")}>Exportar JSON</button>
      </form>
      {error ? <div style={{ color: "#f87171" }}>{error}</div> : null}
      {loading ? <div>Cargando…</div> : (
        <table>
          <thead><tr><th>Fecha</th><th>Usuario</th><th>Módulo</th><th>Acción</th><th>Entidad</th><th>Meta</th></tr></thead>
          <tbody>
            {rows.map((r,i)=>(
              <tr key={i}>
                <td>{new Date(r.ts).toLocaleString()}</td>
                <td>{r.userId || "-"}</td>
                <td>{r.module}</td>
                <td>{r.action}</td>
                <td>{r.entityId || "-"}</td>
                <td><pre style={{whiteSpace:"pre-wrap"}}>{JSON.stringify(r.meta||{}, null, 2)}</pre></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div style={{ marginTop: "0.75rem", fontSize: "0.9rem", opacity: 0.8 }}>
        Total: {pagination.total} registros · Límite actual: {pagination.limit}
      </div>
    </div>
  );
}
// [PACK26-AUDIT-PAGE-END]
