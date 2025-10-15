import { FormEvent, useCallback, useEffect, useState } from "react";
import { AuditLogEntry, getAuditLogs } from "../../../api";
import { useDashboard } from "../../dashboard/context/DashboardContext";

type Props = {
  token: string;
};

function AuditLog({ token }: Props) {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [limit, setLimit] = useState(50);
  const [actionFilter, setActionFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { pushToast } = useDashboard();

  const loadLogs = useCallback(
    async ({ limitOverride, action, notify }: { limitOverride?: number; action?: string; notify?: boolean } = {}) => {
      try {
        if (!notify) {
          setLoading(true);
          setError(null);
        }
        const effectiveLimit = limitOverride ?? limit;
        const effectiveAction = action ?? (actionFilter ? actionFilter.trim() : undefined);
        const data = await getAuditLogs(token, effectiveLimit, effectiveAction);
        setLogs((previous) => {
          if (notify && previous.length > 0 && data.length > 0 && data[0].id !== previous[0].id) {
            pushToast({ message: `Nueva acción registrada: ${data[0].action}`, variant: "info" });
          }
          return data;
        });
        if (!notify) {
          setError(null);
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : "No fue posible consultar la bitácora";
        if (!notify) {
          setError(message);
        }
        pushToast({ message, variant: "error" });
      } finally {
        if (!notify) {
          setLoading(false);
        }
      }
    },
    [actionFilter, limit, pushToast, token]
  );

  useEffect(() => {
    loadLogs({ notify: false });
  }, [loadLogs]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      loadLogs({ notify: true });
    }, 45000);
    return () => window.clearInterval(interval);
  }, [loadLogs]);

  const handleFilter = (event: FormEvent) => {
    event.preventDefault();
    loadLogs({ limitOverride: limit, action: actionFilter ? actionFilter.trim() : undefined, notify: false });
  };

  return (
    <section className="card audit-card fade-in">
      <header className="card-header">
        <h2 className="accent-title">Bitácora de auditoría</h2>
        <p className="card-subtitle">Revisión en tiempo real de acciones sensibles registradas por el backend.</p>
      </header>
      <form className="audit-filters" onSubmit={handleFilter}>
        <label>
          <span>Acción</span>
          <input
            type="text"
            placeholder="Ej. sale_registered"
            value={actionFilter}
            onChange={(event) => setActionFilter(event.target.value)}
          />
        </label>
        <label>
          <span>Límite</span>
          <input
            type="number"
            min={10}
            max={500}
            value={limit}
            onChange={(event) => setLimit(Number(event.target.value))}
          />
        </label>
        <button className="btn" type="submit" disabled={loading}>
          Aplicar filtros
        </button>
      </form>
      {error && <p className="error-text">{error}</p>}
      {loading ? (
        <p>Cargando eventos...</p>
      ) : (
        <div className="audit-log-table">
          <table>
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Acción</th>
                <th>Entidad</th>
                <th>Detalle</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id}>
                  <td>{new Date(log.created_at).toLocaleString()}</td>
                  <td>{log.action}</td>
                  <td>
                    {log.entity_type} #{log.entity_id}
                  </td>
                  <td>{log.details ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default AuditLog;
