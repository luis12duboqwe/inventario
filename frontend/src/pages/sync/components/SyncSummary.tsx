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
}: SyncSummaryProps) {
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
