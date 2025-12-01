import { useMemo } from "react";
import { AlertTriangle, Activity, RefreshCw, ServerCrash } from "lucide-react";

import Button from "../../../shared/components/ui/Button";
import { Skeleton } from "@/ui/Skeleton";
import { useDashboard } from "../context/DashboardContext";

function formatSeconds(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "Sin datos";
  }
  if (value < 1) {
    return "< 1 s";
  }
  const minutes = Math.floor(value / 60);
  const seconds = Math.round(value % 60);
  if (minutes > 0) {
    return seconds > 0 ? `${minutes} min ${seconds} s` : `${minutes} min`;
  }
  return `${Math.round(value)} s`;
}

function resolveLatencyTone(value: number | null | undefined): "ok" | "warn" | "crit" {
  if (value === null || value === undefined) {
    return "ok";
  }
  if (value <= 60) {
    return "ok";
  }
  if (value <= 180) {
    return "warn";
  }
  return "crit";
}

function TechMonitor() {
  const {
    observability,
    observabilityError,
    observabilityLoading,
    refreshObservability,
  } = useDashboard();

  const latencySummary = observability?.latency;
  const syncSummary = observability?.sync;
  const notifications = observability?.notifications ?? [];
  const logs = observability?.logs ?? [];
  const systemErrors = observability?.system_errors ?? [];

  const generatedAtLabel = useMemo(() => {
    if (!observability?.generated_at) {
      return "Sin actualizaciones recientes";
    }
    return new Date(observability.generated_at).toLocaleString("es-HN", {
      dateStyle: "short",
      timeStyle: "short",
    });
  }, [observability?.generated_at]);

  const latencyCards = useMemo(
    () => [
      {
        id: "avg",
        title: "Latencia promedio",
        value: formatSeconds(latencySummary?.average_seconds ?? null),
        tone: resolveLatencyTone(latencySummary?.average_seconds ?? null),
      },
      {
        id: "p95",
        title: "Latencia p95",
        value: formatSeconds(latencySummary?.percentile_95_seconds ?? null),
        tone: resolveLatencyTone(latencySummary?.percentile_95_seconds ?? null),
      },
      {
        id: "max",
        title: "Latencia máxima",
        value: formatSeconds(latencySummary?.max_seconds ?? null),
        tone: resolveLatencyTone(latencySummary?.max_seconds ?? null),
      },
    ],
    [latencySummary?.average_seconds, latencySummary?.max_seconds, latencySummary?.percentile_95_seconds],
  );

  const hasSnapshot = Boolean(observability);
  const showSkeleton = observabilityLoading && !hasSnapshot;
  const syncStats = syncSummary?.outbox_stats ?? [];
  const totalPending = syncSummary?.total_pending ?? 0;
  const totalFailed = syncSummary?.total_failed ?? 0;
  const hybridPercent = syncSummary?.hybrid_progress?.percent ?? null;

  return (
    <section className="tech-monitor" aria-labelledby="tech-monitor-title">
      <div className="tech-monitor__header">
        <div>
          <h2 id="tech-monitor-title">Monitor tecnológico</h2>
          <p>Supervisa la salud híbrida de Softmobile y anticipa incidencias operativas.</p>
          <span className="tech-monitor__meta">Última actualización: {generatedAtLabel}</span>
        </div>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => {
            void refreshObservability();
          }}
          disabled={observabilityLoading}
          leadingIcon={<RefreshCw size={16} aria-hidden="true" />}
        >
          Actualizar
        </Button>
      </div>

      {observabilityError ? (
        <div className="tech-monitor__error" role="alert">
          <AlertTriangle size={16} aria-hidden="true" />
          <span>{observabilityError}</span>
        </div>
      ) : null}

      {showSkeleton ? (
        <div className="tech-monitor__skeleton" aria-busy="true" role="status">
          <Skeleton className="tech-monitor__skeleton-card" />
          <Skeleton className="tech-monitor__skeleton-card" />
          <Skeleton className="tech-monitor__skeleton-card" />
        </div>
      ) : hasSnapshot ? (
        <div className="tech-monitor__content">
          <div className="tech-monitor__metrics" role="list">
            {latencyCards.map((card) => (
              <article
                key={card.id}
                className={`tech-monitor__card tech-monitor__card--${card.tone}`}
                role="listitem"
              >
                <h3>{card.title}</h3>
                <p className="tech-monitor__card-value">{card.value}</p>
                <span className="tech-monitor__card-caption">Cola híbrida y outbox local</span>
              </article>
            ))}
          </div>

          <div className="tech-monitor__grid">
            <section className="tech-monitor__panel" aria-labelledby="tech-sync-heading">
              <header className="tech-monitor__panel-header">
                <div>
                  <h3 id="tech-sync-heading">Sincronización híbrida</h3>
                  <p className="tech-monitor__panel-subtitle">
                    {`Pendientes: ${totalPending} · Fallidos: ${totalFailed}`}
                    {hybridPercent !== null ? ` · Avance ${hybridPercent.toFixed(1)}%` : ""}
                  </p>
                </div>
                <Activity size={18} aria-hidden="true" />
              </header>
              {syncStats.length === 0 ? (
                <p className="tech-monitor__empty">Sin eventos registrados en la cola híbrida.</p>
              ) : (
                <div className="tech-monitor__table-wrapper">
                  <table className="tech-monitor__table">
                    <thead>
                      <tr>
                        <th scope="col">Entidad</th>
                        <th scope="col">Pendientes</th>
                        <th scope="col">Fallidos</th>
                        <th scope="col">Antigüedad</th>
                      </tr>
                    </thead>
                    <tbody>
                      {syncStats.map((stat) => (
                        <tr key={`${stat.entity_type}-${stat.priority}`}>
                          <th scope="row">{stat.entity_type}</th>
                          <td>{stat.pending}</td>
                          <td className={stat.failed > 0 ? "tech-monitor__cell-alert" : undefined}>{stat.failed}</td>
                          <td>{formatSeconds(stat.oldest_pending_seconds ?? null)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className="tech-monitor__panel" aria-labelledby="tech-alerts-heading">
              <header className="tech-monitor__panel-header">
                <div>
                  <h3 id="tech-alerts-heading">Alertas tempranas</h3>
                  <p className="tech-monitor__panel-subtitle">
                    {notifications.length > 0
                      ? `${notifications.length} incidencias vigiladas`
                      : "Sin incidencias críticas"}
                  </p>
                </div>
                <AlertTriangle size={18} aria-hidden="true" />
              </header>
              {notifications.length === 0 ? (
                <p className="tech-monitor__empty">Todo en orden. Continúa monitoreando para reaccionar a tiempo.</p>
              ) : (
                <ul className="tech-monitor__list">
                  {notifications.map((notification) => (
                    <li key={notification.id} className={`tech-monitor__alert tech-monitor__alert--${notification.severity.toLowerCase()}`}>
                      <strong>{notification.title}</strong>
                      <p>{notification.message}</p>
                      {notification.occurred_at ? (
                        <span className="tech-monitor__alert-meta">
                          {new Date(notification.occurred_at).toLocaleString("es-HN", {
                            dateStyle: "short",
                            timeStyle: "short",
                          })}
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          <div className="tech-monitor__logs">
            <section className="tech-monitor__panel" aria-labelledby="tech-logs-heading">
              <header className="tech-monitor__panel-header">
                <div>
                  <h3 id="tech-logs-heading">Logs recientes</h3>
                  <p className="tech-monitor__panel-subtitle">Seguimiento de eventos operativos críticos.</p>
                </div>
                <ServerCrash size={18} aria-hidden="true" />
              </header>
              {logs.length === 0 ? (
                <p className="tech-monitor__empty">Sin registros relevantes en las últimas horas.</p>
              ) : (
                <ul className="tech-monitor__list tech-monitor__list--compact">
                  {logs.slice(0, 4).map((entry) => (
                    <li key={`log-${entry.id_log}`}>
                      <strong>{entry.modulo}</strong>
                      <p>{entry.descripcion}</p>
                      <span className="tech-monitor__alert-meta">
                        {new Date(entry.fecha).toLocaleString("es-HN", {
                          dateStyle: "short",
                          timeStyle: "short",
                        })}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="tech-monitor__panel" aria-labelledby="tech-errors-heading">
              <header className="tech-monitor__panel-header">
                <div>
                  <h3 id="tech-errors-heading">Errores de sistema</h3>
                  <p className="tech-monitor__panel-subtitle">Escala a TI cuando identifiques tendencias.</p>
                </div>
                <ServerCrash size={18} aria-hidden="true" />
              </header>
              {systemErrors.length === 0 ? (
                <p className="tech-monitor__empty">Sin errores críticos registrados.</p>
              ) : (
                <ul className="tech-monitor__list tech-monitor__list--compact">
                  {systemErrors.slice(0, 4).map((entry) => (
                    <li key={`error-${entry.id_error}`}>
                      <strong>{entry.modulo}</strong>
                      <p>{entry.mensaje}</p>
                      <span className="tech-monitor__alert-meta">
                        {new Date(entry.fecha).toLocaleString("es-HN", {
                          dateStyle: "short",
                          timeStyle: "short",
                        })}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </div>
      ) : (
        <div className="tech-monitor__empty">Aún no se han generado métricas de observabilidad.</div>
      )}
    </section>
  );
}

export default TechMonitor;
