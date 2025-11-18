// [PACK35-frontend]
import { useEffect, useMemo, useState } from "react";

import type { SyncClientFlushSummary } from "../services/syncClient";
import type { LocalSyncQueueItem } from "../services/syncClient";

type Props = {
  pending: LocalSyncQueueItem[];
  history: LocalSyncQueueItem[];
  loading: boolean;
  online: boolean;
  onFlush: () => Promise<SyncClientFlushSummary>;
  onGenerateDemo: () => Promise<LocalSyncQueueItem>;
  lastSummary: SyncClientFlushSummary | null;
  resetSummary: () => void;
  progress: {
    percent: number;
    total: number;
    sent: number;
    pending: number;
    failed: number;
  };
  forecast: {
    lookbackMinutes: number;
    eventsPerMinute: number;
    successRate: number;
    processedRecent: number;
    backlogPending: number;
    backlogFailed: number;
    backlogTotal: number;
    estimatedMinutesRemaining: number | null;
    estimatedCompletion: string | null;
    generatedAt: string | null;
  };
  modules: Array<{
    module: string;
    label: string;
    percent: number;
    total: number;
    processed: number;
    pending: number;
    failed: number;
    queue: { total: number; processed: number; pending: number; failed: number };
    outbox: { total: number; processed: number; pending: number; failed: number };
  }>;
};

function formatTimestamp(value: number | null | undefined): string {
  if (!value) {
    return "—";
  }
  try {
    return new Date(value).toLocaleString("es-MX");
  } catch {
    return "—";
  }
}

const statusLabel: Record<string, string> = {
  pending: "Pendiente",
  sending: "Enviando",
  sent: "Enviado",
  failed: "Fallido",
};

function statusClass(status: string): string {
  switch (status) {
    case "sent":
      return "badge success";
    case "failed":
      return "badge warning";
    case "sending":
      return "badge info";
    default:
      return "badge neutral";
  }
}

export function HybridQueuePanel({
  pending,
  history,
  loading,
  online,
  onFlush,
  onGenerateDemo,
  lastSummary,
  resetSummary,
  progress,
  forecast,
  modules,
}: Props) {
  const [flushing, setFlushing] = useState(false);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!lastSummary) {
      return;
    }
    if (typeof window === "undefined") {
      return;
    }
    const timeout = window.setTimeout(() => resetSummary(), 4000);
    return () => window.clearTimeout(timeout);
  }, [lastSummary, resetSummary]);

  const summaryMessage = useMemo(() => {
    if (!lastSummary) {
      return null;
    }
    if (lastSummary.sent > 0) {
      return `${lastSummary.sent} evento(s) enviados exitosamente.`;
    }
    if (lastSummary.failed > 0) {
      return `${lastSummary.failed} evento(s) fallaron; se reintentará automáticamente.`;
    }
    return null;
  }, [lastSummary]);

  const handleFlush = async () => {
    if (flushing) {
      return;
    }
    setFlushing(true);
    try {
      await onFlush();
    } finally {
      setFlushing(false);
    }
  };

  const handleDemo = async () => {
    if (creating) {
      return;
    }
    setCreating(true);
    try {
      await onGenerateDemo();
    } finally {
      setCreating(false);
    }
  };

  const etaMinutes =
    typeof forecast.estimatedMinutesRemaining === "number"
      ? Math.max(0, Math.round(forecast.estimatedMinutesRemaining))
      : null;
  const etaDate = forecast.estimatedCompletion
    ? new Date(forecast.estimatedCompletion).toLocaleString("es-MX")
    : null;
  const moduleBreakdown = useMemo(() => {
    if (!modules || modules.length === 0) {
      return [] as Props["modules"];
    }
    return [...modules]
      .filter((module) => module.total > 0)
      .sort(
        (a, b) => b.pending + b.failed - (a.pending + a.failed) || b.percent - a.percent,
      )
      .slice(0, 5);
  }, [modules]);

  return (
    <section className="hybrid-queue card">
      <header className="hybrid-queue__header">
        <div>
          <h2>Cola local híbrida</h2>
          <p className="hybrid-queue__subtitle">
            Eventos que se conservan sin conexión y se reintentan automáticamente.
          </p>
        </div>
        <div className="hybrid-queue__actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleDemo}
            disabled={creating}
          >
            {creating ? "Generando…" : "Generar evento demo"}
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleFlush}
            disabled={flushing || loading}
          >
            {flushing ? "Enviando…" : "Forzar envío"}
          </button>
        </div>
      </header>
      <div className="hybrid-queue__status">
        <span className={online ? "badge success" : "badge warning"}>
          {online ? "Conexión activa" : "Sin conexión"}
        </span>
        <span className="badge neutral">Pendientes: {pending.length}</span>
      </div>
      <div className="hybrid-queue__progress">
        <div className="hybrid-queue__progress-meta">
          <strong>Avance de sincronización local:</strong>
          <span>{progress.percent}% completado</span>
          <span>
            {progress.sent} de {progress.total || progress.sent || 0} evento(s) enviados
          </span>
          {progress.failed > 0 ? (
            <span className="hybrid-queue__progress-alert">{progress.failed} evento(s) con error en espera de nuevo intento</span>
          ) : null}
        </div>
        <div className="hybrid-queue__progress-bar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress.percent} role="progressbar">
          <div className="hybrid-queue__progress-bar-fill" style={{ width: `${progress.percent}%` }} />
        </div>
      </div>
      <div className="hybrid-queue__insights">
        <div className="hybrid-queue__insight">
          <span className="hybrid-queue__insight-label">Ritmo actual</span>
          <strong>{forecast.eventsPerMinute.toFixed(2)} ev/min</strong>
          <small>Últimos {forecast.lookbackMinutes || 0} minutos · {forecast.processedRecent} evento(s)</small>
        </div>
        <div className="hybrid-queue__insight">
          <span className="hybrid-queue__insight-label">Tasa de éxito</span>
          <strong>{forecast.successRate.toFixed(1)}%</strong>
          <small>
            {etaMinutes !== null ? `ETA ${etaMinutes} min` : "ETA no disponible"}
            {etaDate ? ` · Fin estimado ${etaDate}` : ""}
          </small>
        </div>
        <div className="hybrid-queue__insight">
          <span className="hybrid-queue__insight-label">Backlog híbrido</span>
          <strong>{forecast.backlogTotal}</strong>
          <small>
            Pendientes {forecast.backlogPending} · Fallidos {forecast.backlogFailed}
          </small>
        </div>
      </div>
      <div className="hybrid-queue__modules">
        <h3>Desglose por módulo</h3>
        {moduleBreakdown.length === 0 ? (
          <p className="hybrid-queue__hint">Sin eventos registrados por módulo.</p>
        ) : (
          <ul className="hybrid-queue__module-list">
            {moduleBreakdown.map((module) => {
              const backlog = module.pending + module.failed;
              return (
                <li key={module.module} className="hybrid-queue__module-item">
                  <div className="hybrid-queue__module-header">
                    <span>{module.label}</span>
                    <span>{module.percent}%</span>
                  </div>
                  <div
                    className="hybrid-queue__module-bar"
                    role="progressbar"
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={module.percent}
                  >
                    <div className="hybrid-queue__module-bar-fill" style={{ width: `${module.percent}%` }} />
                  </div>
                  <div className="hybrid-queue__module-meta">
                    <span>{module.processed}/{module.total} enviados</span>
                    <span>Pendientes {module.pending}</span>
                    {module.failed > 0 ? (
                      <span className="hybrid-queue__module-failed">
                        Fallidos {module.failed}
                      </span>
                    ) : null}
                  </div>
                  <div className="hybrid-queue__module-sources">
                    <span>Servidor {module.queue.processed}/{module.queue.total}</span>
                    <span>Outbox {module.outbox.processed}/{module.outbox.total}</span>
                    {backlog > 0 ? (
                      <span className="hybrid-queue__module-backlog">Backlog {backlog}</span>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
      {summaryMessage ? <p className="hybrid-queue__summary">{summaryMessage}</p> : null}
      <div className="hybrid-queue__body">
        <div className="queue-column">
          <h3>Pendientes</h3>
          {loading ? (
            <p className="hybrid-queue__hint">Cargando cola local…</p>
          ) : pending.length === 0 ? (
            <p className="hybrid-queue__hint">No hay eventos pendientes. Genera un evento demo para probar.</p>
          ) : (
            <ul className="queue-list">
              {pending.map((item) => (
                <li key={item.id} className="queue-item">
                  <div className="queue-item__header">
                    <span className={statusClass(item.status)}>{statusLabel[item.status] ?? item.status}</span>
                    <span className="queue-item__type">{item.eventType}</span>
                  </div>
                  <p className="queue-item__meta">
                    Intentos: {item.attempts} · Último cambio: {formatTimestamp(item.updatedAt)}
                  </p>
                  {item.lastError ? <p className="queue-item__error">⚠️ {item.lastError}</p> : null}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="queue-column">
          <h3>Historial reciente</h3>
          {history.length === 0 ? (
            <p className="hybrid-queue__hint">Aún no se han enviado eventos desde esta sesión.</p>
          ) : (
            <table className="queue-table">
              <thead>
                <tr>
                  <th>Evento</th>
                  <th>Estado</th>
                  <th>Actualizado</th>
                </tr>
              </thead>
              <tbody>
                {history.slice(0, 8).map((item) => (
                  <tr key={`history-${item.id}`}>
                    <td>{item.eventType}</td>
                    <td>
                      <span className={statusClass(item.status)}>{statusLabel[item.status] ?? item.status}</span>
                    </td>
                    <td>{formatTimestamp(item.updatedAt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </section>
  );
}

export default HybridQueuePanel;
