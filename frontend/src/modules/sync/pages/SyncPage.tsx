import { useCallback, useEffect, useMemo } from "react";

import { downloadInventoryCsv } from "../../../api";
import SyncSummary from "../../../pages/sync/components/SyncSummary";
import SyncPanel from "../components/SyncPanel";
import { HybridQueuePanel } from "../components/HybridQueuePanel";
import { useSyncModule } from "../hooks/useSyncModule";
import { useSyncQueue } from "../hooks/useSyncQueue";

function ensureReason(raw: string | null | undefined): string | null {
  if (!raw) {
    return null;
  }
  const normalized = raw.trim();
  if (normalized.length < 5) {
    return null;
  }
  return normalized;
}

export default function SyncPage() {
  const {
    handleSync,
    handleBackup,
    downloadInventoryReport,
    syncStatus,
    enableHybridPrep,
    outbox,
    outboxError,
    refreshOutbox,
    handleRetryOutbox,
    outboxStats,
    syncQueueSummary,
    syncHybridProgress,
    syncHybridForecast,
    syncHybridBreakdown,
    syncHybridOverview,
    syncHistory,
    syncHistoryError,
    refreshSyncHistory,
    refreshSyncQueueSummary,
    token,
    pushToast,
  } = useSyncModule();

  const {
    pending,
    history,
    loading,
    online,
    enqueueDemo,
    flush,
    lastSummary,
    resetSummary,
    progress,
  } = useSyncQueue(token);

  useEffect(() => {
    if (!enableHybridPrep) {
      return;
    }
    void refreshSyncQueueSummary();
    void refreshOutbox();
    void refreshSyncHistory();
  }, [enableHybridPrep, refreshOutbox, refreshSyncHistory, refreshSyncQueueSummary]);

  const handleManualSync = useCallback(async () => {
    await handleSync();
    if (enableHybridPrep) {
      await refreshSyncQueueSummary();
      await refreshOutbox();
    }
  }, [enableHybridPrep, handleSync, refreshOutbox, refreshSyncQueueSummary]);

  const handleManualBackup = useCallback(async () => {
    const input = ensureReason(
      typeof window === "undefined"
        ? "Respaldo manual desde sincronización"
        : window.prompt("Motivo corporativo para el respaldo", "Respaldo manual desde sincronización"),
    );
    if (!input) {
      pushToast({ message: "Se requiere un motivo corporativo de al menos 5 caracteres.", variant: "warning" });
      return;
    }
    await handleBackup(input);
  }, [handleBackup, pushToast]);

  const handleDownloadPdf = useCallback(async () => {
    const input = ensureReason(
      typeof window === "undefined"
        ? "Reporte inventario sincronización"
        : window.prompt("Motivo para descargar el PDF", "Reporte inventario sincronización"),
    );
    if (!input) {
      pushToast({ message: "No se generó el PDF porque falta el motivo corporativo.", variant: "warning" });
      return;
    }
    try {
      await downloadInventoryReport(input);
      pushToast({ message: "PDF de inventario generado correctamente.", variant: "success" });
    } catch (error) {
      const message = error instanceof Error ? error.message : "No fue posible descargar el PDF";
      pushToast({ message, variant: "error" });
    }
  }, [downloadInventoryReport, pushToast]);

  const handleExportCsv = useCallback(async () => {
    if (!token) {
      pushToast({ message: "No hay sesión activa para descargar el CSV.", variant: "error" });
      return;
    }
    const input = ensureReason(
      typeof window === "undefined"
        ? "Exportación inventario sincronización"
        : window.prompt("Motivo para exportar el CSV", "Exportación inventario sincronización"),
    );
    if (!input) {
      pushToast({ message: "Exportación cancelada: indica un motivo corporativo válido.", variant: "warning" });
      return;
    }
    try {
      await downloadInventoryCsv(token, input);
      pushToast({ message: "CSV de inventario en cola de descarga.", variant: "success" });
    } catch (error) {
      const message = error instanceof Error ? error.message : "No fue posible generar el CSV";
      pushToast({ message, variant: "error" });
    }
  }, [pushToast, token]);

  const hybridForecast = useMemo(() => {
    if (syncHybridForecast) {
      return {
        lookbackMinutes: syncHybridForecast.lookback_minutes,
        eventsPerMinute: syncHybridForecast.events_per_minute,
        successRate: syncHybridForecast.success_rate,
        processedRecent: syncHybridForecast.processed_recent,
        backlogPending: syncHybridForecast.backlog_pending,
        backlogFailed: syncHybridForecast.backlog_failed,
        backlogTotal: syncHybridForecast.backlog_total,
        estimatedMinutesRemaining: syncHybridForecast.estimated_minutes_remaining,
        estimatedCompletion: syncHybridForecast.estimated_completion,
        generatedAt: syncHybridForecast.generated_at,
      };
    }
    const failedLocal = history.filter((item) => item.status === "failed").length;
    const pendingLocal = pending.length;
    return {
      lookbackMinutes: 15,
      eventsPerMinute: 0,
      successRate: 0,
      processedRecent: history.length,
      backlogPending: pendingLocal,
      backlogFailed: failedLocal,
      backlogTotal: pendingLocal + failedLocal,
      estimatedMinutesRemaining: null,
      estimatedCompletion: null,
      generatedAt: null,
    };
  }, [history, pending, syncHybridForecast]);

  const modules = useMemo(() => {
    if (syncHybridBreakdown.length > 0) {
      return syncHybridBreakdown;
    }
    return [];
  }, [syncHybridBreakdown]);

  const historyPreview = useMemo(() => syncHistory.slice(0, 6), [syncHistory]);

  return (
    <div className="sync-dashboard">
      <header className="sync-dashboard__header">
        <div>
          <h1>Sincronización corporativa</h1>
          <p>
            Gestiona las sincronizaciones híbridas, monitorea la cola local y revisa los eventos del servidor.
          </p>
          {syncStatus ? <span className="pill accent">{syncStatus}</span> : null}
        </div>
        <SyncPanel
          onSync={handleManualSync}
          onBackup={handleManualBackup}
          onDownloadPdf={handleDownloadPdf}
          onExportCsv={handleExportCsv}
          syncStatus={syncStatus}
        />
      </header>

      <SyncSummary
        summary={syncQueueSummary}
        progress={syncHybridProgress}
        forecast={syncHybridForecast ?? null}
        breakdown={modules}
        overview={syncHybridOverview}
      />

      <HybridQueuePanel
        pending={pending}
        history={history}
        loading={loading}
        online={online}
        onFlush={flush}
        onGenerateDemo={enqueueDemo}
        lastSummary={lastSummary}
        resetSummary={resetSummary}
        progress={progress}
        forecast={hybridForecast}
        modules={modules}
      />

      <section className="sync-dashboard__logs" aria-live="polite">
        <div className="sync-dashboard__header">
          <h2>Historial de sincronización</h2>
          <button type="button" className="btn btn-ghost" onClick={() => void refreshSyncHistory()}>
            Actualizar historial
          </button>
        </div>
        {syncHistoryError ? <p className="sync-log__error">{syncHistoryError}</p> : null}
        <div className="sync-history-grid">
          {historyPreview.length === 0 ? (
            <p className="hybrid-queue__hint">Aún no hay sesiones registradas en esta instancia.</p>
          ) : (
            historyPreview.map((store) => (
              <article key={store.store_name} className="sync-history-item">
                <h3>{store.store_name}</h3>
                <ul>
                  {store.sessions.slice(0, 4).map((session) => (
                    <li key={session.id} className="sync-history-line">
                      <span className="pill neutral">{session.status}</span>
                      <span className="sync-history-mode">{session.mode}</span>
                      <span className="sync-log__time">Inicio: {new Date(session.started_at).toLocaleString("es-MX")}</span>
                      {session.finished_at ? (
                        <span className="sync-log__time">Fin: {new Date(session.finished_at).toLocaleString("es-MX")}</span>
                      ) : (
                        <span className="sync-log__time">En progreso</span>
                      )}
                      {session.error_message ? (
                        <span className="sync-history-error">{session.error_message}</span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </article>
            ))
          )}
        </div>
      </section>

      <section className="sync-dashboard__logs">
        <div className="sync-dashboard__header">
          <h2>Outbox corporativa</h2>
          <div className="hybrid-queue__actions">
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => void refreshOutbox()}
            >
              Refrescar outbox
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={outbox.length === 0}
              onClick={() => void handleRetryOutbox()}
            >
              Reintentar eventos
            </button>
          </div>
        </div>
        {outboxError ? <p className="sync-log__error">{outboxError}</p> : null}
        {outboxStats.length === 0 ? (
          <p className="hybrid-queue__hint">No hay eventos en la outbox central.</p>
        ) : (
          <div className="card">
            <table className="sync-branch-table">
              <thead>
                <tr>
                  <th>Entidad</th>
                  <th>Prioridad</th>
                  <th>Total</th>
                  <th>Pendientes</th>
                  <th>Fallidos</th>
                  <th>Última actualización</th>
                </tr>
              </thead>
              <tbody>
                {outboxStats.map((entry) => (
                  <tr key={`${entry.entity_type}-${entry.priority}`}>
                    <td>{entry.entity_type}</td>
                    <td>{entry.priority}</td>
                    <td>{entry.total}</td>
                    <td>{entry.pending}</td>
                    <td>{entry.failed}</td>
                    <td>{entry.latest_update ? new Date(entry.latest_update).toLocaleString("es-MX") : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
