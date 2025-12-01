// [PACK26-AUDIT-PAGE-START]
import { FormEvent, useEffect, useState } from "react";
import { downloadBlob } from "../../../lib/download";
import { useAuthz, PERMS } from "../../../auth/useAuthz";
import { fetchAuditEvents, downloadAuditExport, AuditListResponse } from "../../../services/audit";

type Row = {
  ts: number;
  userId: string | null;
  module: string;
  action: string;
  entityId: string | null;
  meta: Record<string, unknown> | null;
};

export default function AuditPage() {
  const { can } = useAuthz();
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState<{ total: number; limit: number; offset: number }>({
    total: 0,
    limit: 100,
    offset: 0,
  });
  const [filters, setFilters] = useState({ userId: "", module: "", from: "", to: "" });
  const [appliedFilters, setAppliedFilters] = useState({
    userId: "",
    module: "",
    from: "",
    to: "",
  });

  useEffect(() => {
    if (!can(PERMS.AUDIT_VIEW)) return;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        // // [PACK32-33-FE] Prefiere backend real con filtros y paginación
        const response: AuditListResponse = await fetchAuditEvents({
          ...Object.fromEntries(Object.entries(appliedFilters).filter(([, value]) => value)),
          limit: pagination.limit,
          offset: pagination.offset,
        });
        setRows(
          (response.items || []).map((item) => ({
            ts: typeof item.ts === "string" ? new Date(item.ts).getTime() : item.ts,
            userId: item.userId ?? null,
            module: item.module,
            action: item.action,
            entityId: item.entityId ?? null,
            meta: (item.meta as Record<string, unknown> | null | undefined) ?? null,
          })),
        );
        setPagination((prev) => {
          const next = { total: response.total, limit: response.limit, offset: response.offset };
          if (
            prev.total === next.total &&
            prev.limit === next.limit &&
            prev.offset === next.offset
          ) {
            return prev;
          }
          return next;
        });
      } catch (err) {
        // fallback: mostrar cola local si no hay backend
        try {
          const localRaw = JSON.parse(localStorage.getItem("sm_ui_audit_queue") || "[]");
          const local: Row[] = Array.isArray(localRaw)
            ? localRaw.map(
                (entry): Row => ({
                  ts: typeof entry?.ts === "number" ? entry.ts : Date.now(),
                  userId: typeof entry?.userId === "string" ? entry.userId : null,
                  module: typeof entry?.module === "string" ? entry.module : "OTHER",
                  action: typeof entry?.action === "string" ? entry.action : "unknown",
                  entityId: typeof entry?.entityId === "string" ? entry.entityId : null,
                  meta: (entry?.meta as Record<string, unknown> | null | undefined) ?? null,
                }),
              )
            : [];
          setRows(local);
          setPagination((prev) => {
            const next = { total: local.length, limit: local.length || 1, offset: 0 };
            if (
              prev.total === next.total &&
              prev.limit === next.limit &&
              prev.offset === next.offset
            ) {
              return prev;
            }
            return next;
          });
        } catch {}
        setError(err instanceof Error ? err.message : "No se pudo contactar la API de auditoría");
      } finally {
        setLoading(false);
      }
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
      setError(err instanceof Error ? err.message : `No se pudo exportar la bitácora (${format})`);
    }
  }

  if (!can(PERMS.AUDIT_VIEW)) return <div>No autorizado</div>;

  return (
    <div data-testid="audit-page">
      <h2>Auditoría UI</h2>
      <form onSubmit={handleFilterSubmit} className="audit-page-form">
        <label className="audit-page-label">
          Usuario
          <input
            value={filters.userId}
            onChange={(e) => setFilters((prev) => ({ ...prev, userId: e.target.value }))}
            placeholder="userId"
          />
        </label>
        <label className="audit-page-label">
          Módulo
          <input
            value={filters.module}
            onChange={(e) => setFilters((prev) => ({ ...prev, module: e.target.value }))}
            placeholder="module"
          />
        </label>
        <label className="audit-page-label">
          Desde
          <input
            type="datetime-local"
            value={filters.from}
            onChange={(e) => setFilters((prev) => ({ ...prev, from: e.target.value }))}
          />
        </label>
        <label className="audit-page-label">
          Hasta
          <input
            type="datetime-local"
            value={filters.to}
            onChange={(e) => setFilters((prev) => ({ ...prev, to: e.target.value }))}
          />
        </label>
        <button type="submit">Aplicar filtros</button>
        <button type="button" onClick={() => handleExport("csv")}>
          Exportar CSV
        </button>
        <button type="button" onClick={() => handleExport("json")}>
          Exportar JSON
        </button>
      </form>
      {error ? <div className="audit-page-error">{error}</div> : null}
      {loading ? (
        <div>Cargando…</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Usuario</th>
              <th>Módulo</th>
              <th>Acción</th>
              <th>Entidad</th>
              <th>Meta</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td>{new Date(r.ts).toLocaleString()}</td>
                <td>{r.userId ?? "-"}</td>
                <td>{r.module}</td>
                <td>{r.action}</td>
                <td>{r.entityId ?? "-"}</td>
                <td>
                  <pre className="audit-page-meta">{JSON.stringify(r.meta ?? {}, null, 2)}</pre>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="audit-page-footer">
        Total: {pagination.total} registros · Límite actual: {pagination.limit}
      </div>
    </div>
  );
}
// [PACK26-AUDIT-PAGE-END]
