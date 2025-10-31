import type { ModuleStatus } from "../../../shared/components/ModuleHeader";
import type { RecentSyncLog } from "../../../types/sync";

import { Repeat } from "lucide-react";

import ModuleHeader from "../../../shared/components/ModuleHeader";

const moduleStatusBadgeClass: Record<ModuleStatus, string> = {
  ok: "badge success",
  warning: "badge warning",
  critical: "badge critical",
};

type SyncSummaryProps = {
  moduleStatus: ModuleStatus;
  moduleStatusLabel: string;
  currentSyncLabel: string;
  hasSyncFailure: boolean;
  branchCount: number;
  totalInventoryValue: number;
  totalPendingOutbox: number;
  totalOpenConflicts: number;
  totalPendingTransfers: number;
  formatCurrency: (value: number) => string;
  recentSyncLogs: RecentSyncLog[];
  lastSyncExecution: RecentSyncLog | null;
  enableHybridPrep: boolean;
  onRefreshOutbox: () => void;
  formatDateTime: (value?: string | null) => string;
  hybridProgress: {
    percent: number;
    total: number;
    processed: number;
    pending: number;
    failed: number;
    server: {
      percent: number;
      total: number;
      processed: number;
      pending: number;
      failed: number;
    };
    breakdown: {
      local: { total: number; processed: number; pending: number; failed: number };
      remote: {
        total: number;
        processed: number;
        pending: number;
        failed: number;
        lastUpdated: string | null;
        oldestPending: string | null;
      };
      outbox: {
        total: number;
        processed: number;
        pending: number;
        failed: number;
        lastUpdated: string | null;
        oldestPending: string | null;
      };
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
    }; 
    overview: {
      percent: number;
      generatedAt: string | null;
      remaining: {
        total: number;
        pending: number;
        failed: number;
        remotePending: number;
        outboxPending: number;
        estimatedMinutesRemaining: number | null;
        estimatedCompletion: string | null;
      };
    } | null;
  }; // [PACK35-frontend]
};

function SyncSummary({
  moduleStatus,
  moduleStatusLabel,
  currentSyncLabel,
  hasSyncFailure,
  branchCount,
  totalInventoryValue,
  totalPendingOutbox,
  totalOpenConflicts,
  totalPendingTransfers,
  formatCurrency,
  recentSyncLogs,
  lastSyncExecution,
  enableHybridPrep,
  onRefreshOutbox,
  formatDateTime,
  hybridProgress,
}: SyncSummaryProps) {
  const remoteBreakdown = hybridProgress.breakdown.remote;
  const outboxBreakdown = hybridProgress.breakdown.outbox;
  const moduleBreakdown = hybridProgress.modules ?? [];
  const forecast = hybridProgress.forecast;
  const progressSegments: string[] = [];

  if (hybridProgress.total !== 0) {
    progressSegments.push(
      `Local ${hybridProgress.breakdown.local.processed}/${hybridProgress.breakdown.local.total}`,
      `Procesados totales ${hybridProgress.processed}/${hybridProgress.total}`,
    );

    if (hybridProgress.overview) {
      progressSegments.push(
        `Servidor ${hybridProgress.overview.percent.toFixed(2)}%`,
        `Pendientes totales ${hybridProgress.overview.remaining.total}`,
        `Remotos ${hybridProgress.overview.remaining.remotePending} · Outbox ${hybridProgress.overview.remaining.outboxPending}`,
      );
      if (hybridProgress.overview.remaining.failed > 0) {
        progressSegments.push(`Fallidos críticos ${hybridProgress.overview.remaining.failed}`);
      }
      if (hybridProgress.overview.remaining.estimatedCompletion) {
        progressSegments.push(
          `Final estimado ${formatDateTime(hybridProgress.overview.remaining.estimatedCompletion)}`,
        );
      } else if (hybridProgress.overview.generatedAt) {
        progressSegments.push(`Actualizado ${formatDateTime(hybridProgress.overview.generatedAt)}`);
      }
    } else {
      progressSegments.push(`Central ${hybridProgress.server.percent.toFixed(2)}%`);
    }

    progressSegments.push(`Pendientes ${hybridProgress.pending}`, `Fallidos ${hybridProgress.failed}`);

    if (forecast.processedRecent > 0) {
      progressSegments.push(
        `Procesados ${forecast.processedRecent} ev en ${forecast.lookbackMinutes} min`,
      );
    }
    if (forecast.eventsPerMinute > 0) {
      progressSegments.push(`Ritmo ${forecast.eventsPerMinute.toFixed(2)} ev/min`);
    }
    if (forecast.estimatedMinutesRemaining !== null) {
      progressSegments.push(
        `ETA ${Math.max(0, Math.round(forecast.estimatedMinutesRemaining))} min`,
      );
    }
    if (remoteBreakdown.lastUpdated) {
      progressSegments.push(`Último envío remoto ${formatDateTime(remoteBreakdown.lastUpdated)}`);
    }
    if (remoteBreakdown.oldestPending) {
      progressSegments.push(`Pendiente remoto más antiguo ${formatDateTime(remoteBreakdown.oldestPending)}`);
    }
    if (outboxBreakdown.lastUpdated) {
      progressSegments.push(`Outbox actualizado ${formatDateTime(outboxBreakdown.lastUpdated)}`);
    }
    if (outboxBreakdown.oldestPending) {
      progressSegments.push(
        `Outbox pendiente más antiguo ${formatDateTime(outboxBreakdown.oldestPending)}`,
      );
    }
    if (!hybridProgress.overview?.remaining.estimatedCompletion && forecast.estimatedCompletion) {
      progressSegments.push(`Final estimado ${formatDateTime(forecast.estimatedCompletion)}`);
    }

    if (moduleBreakdown.length > 0) {
      const sortedByBacklog = [...moduleBreakdown]
        .filter((module) => module.total > 0)
        .sort(
          (a, b) => b.pending + b.failed - (a.pending + a.failed) || b.percent - a.percent,
        )
        .slice(0, 2);
      const highlighted = new Set<string>();
      sortedByBacklog.forEach((module) => {
        highlighted.add(module.module);
        progressSegments.push(
          `${module.label}: ${module.processed}/${module.total} (${module.percent}% · Pend ${module.pending})`,
        );
      });
      const failedHighlight = moduleBreakdown.find(
        (module) => module.failed > 0 && !highlighted.has(module.module),
      );
      if (failedHighlight) {
        progressSegments.push(
          `Fallidos ${failedHighlight.label}: ${failedHighlight.failed} evento(s)`,
        );
      }
    }
  }

  return (
    <>
      <ModuleHeader
        icon={<Repeat aria-hidden="true" />}
        title="Sincronización"
        subtitle="Control de sincronizaciones locales, respaldos y versiones distribuidas"
        status={moduleStatus}
        statusLabel={moduleStatusLabel}
        actions={
          <button className="btn btn--ghost" type="button" onClick={onRefreshOutbox}>
            Refrescar cola
          </button>
        }
      />
      <section className="card sync-dashboard">
        <div className="sync-dashboard__header">
          <h2>Dashboard de sincronización</h2>
          <span className={moduleStatusBadgeClass[moduleStatus]}>{moduleStatusLabel}</span>
        </div>
        <div className="sync-dashboard__summary">
          <div className="sync-metric">
            <span>Estado actual</span>
            <strong>{currentSyncLabel}</strong>
            <small>
              {hasSyncFailure
                ? "Atiende los errores pendientes para recuperar la sincronización"
                : "Monitoreo híbrido en ejecución"}
            </small>
          </div>
          <div className="sync-metric">
            <span>Última ejecución</span>
            <strong>{lastSyncExecution ? formatDateTime(lastSyncExecution.startedAt) : "Sin registros"}</strong>
            <small>
              {lastSyncExecution
                ? `${lastSyncExecution.storeName} · ${lastSyncExecution.mode}`
                : "Ejecuta una sincronización manual para registrar actividad"}
            </small>
          </div>
          <div className="sync-metric">
            <span>Sucursales monitoreadas</span>
            <strong>{branchCount}</strong>
            <small>{branchCount === 1 ? "1 tienda activa" : `${branchCount} tiendas activas`}</small>
          </div>
          <div className="sync-metric">
            <span>Inventario monitoreado</span>
            <strong>{branchCount > 0 ? formatCurrency(totalInventoryValue) : "—"}</strong>
            <small>Valor acumulado por sucursal</small>
          </div>
          <div className="sync-metric">
            <span>Cola local pendiente</span>
            <strong>{totalPendingOutbox}</strong>
            <small>{enableHybridPrep ? "Eventos por replicar" : "Habilita el modo híbrido"}</small>
          </div>
          <div className="sync-metric">
            <span>Porcentaje para finalizar todo</span>
            <strong>{hybridProgress.percent.toFixed(2)}%</strong>
            <small>
              {hybridProgress.total === 0
                ? "Sin eventos en la cola híbrida"
                : progressSegments.length > 0
                ? progressSegments.join(" · ")
                : "Sin métricas recientes"}
            </small>
          </div>
          <div className="sync-metric">
            <span>Conflictos abiertos</span>
            <strong>{totalOpenConflicts}</strong>
            <small>{totalOpenConflicts === 1 ? "Un conflicto detectado" : "Conflictos por resolver"}</small>
          </div>
          <div className="sync-metric">
            <span>Transferencias activas</span>
            <strong>{totalPendingTransfers}</strong>
            <small>Solicitadas o en tránsito</small>
          </div>
        </div>
        <div className="sync-dashboard__logs">
          <h3>Últimos registros</h3>
          {recentSyncLogs.length === 0 ? (
            <p className="muted-text">Sin ejecuciones registradas en la bitácora.</p>
          ) : (
            <ul className="sync-log-list">
              {recentSyncLogs.map((log) => (
                <li key={log.id} className="sync-log__item">
                  <div className="sync-log__header">
                    <div
                      className={`badge ${log.status === "exitoso" ? "success" : "warning"}`}
                      aria-label={log.status === "exitoso" ? "Ejecución exitosa" : "Ejecución con fallos"}
                    >
                      {log.status === "exitoso" ? "Exitoso" : "Fallido"}
                    </div>
                    <span className="sync-log__time">{formatDateTime(log.startedAt)}</span>
                  </div>
                  <div className="sync-log__meta">
                    <span>{log.storeName}</span>
                    <span>Modo: {log.mode}</span>
                    {log.finishedAt ? <span>Finalizó {formatDateTime(log.finishedAt)}</span> : null}
                  </div>
                  {log.errorMessage ? <p className="sync-log__error">⚠️ {log.errorMessage}</p> : null}
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </>
  );
}

export type { SyncSummaryProps };
export default SyncSummary;
