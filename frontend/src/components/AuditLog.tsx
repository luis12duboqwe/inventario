import { FormEvent, useEffect, useState } from "react";
import { AuditLogEntry, getAuditLogs } from "../api";

type Props = {
  token: string;
};

function AuditLog({ token }: Props) {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [limit, setLimit] = useState(50);
  const [actionFilter, setActionFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadLogs = async (currentLimit = limit, action?: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await getAuditLogs(token, currentLimit, action);
      setLogs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible consultar la bitácora");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, [token]);

  const handleFilter = (event: FormEvent) => {
    event.preventDefault();
    loadLogs(limit, actionFilter ? actionFilter.trim() : undefined);
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
