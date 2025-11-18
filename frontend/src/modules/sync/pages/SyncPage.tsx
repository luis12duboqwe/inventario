import { useCallback, useEffect, useMemo } from "react";

import { downloadInventoryCsv, retrySyncOutbox } from "../../../api";
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

function formatLatencyMs(value?: number | null): string {
  if (typeof value !== "number" || Number.isNaN(value) || value < 0) {
    return "—";
  }
  if (value < 1000) {
    return `${value} ms`;
  }
  const seconds = value / 1000;
  if (seconds < 60) {
    return `${seconds.toFixed(1)} s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.round(seconds % 60);
  return `${minutes} m ${remaining} s`;
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
    refreshOutboxStats,
    handleRetryOutbox,
    reprioritizeOutbox,
    handleResolveOutboxConflicts,
    outboxStats,
    outboxConflicts,
    lastOutboxConflict,
    syncQueueSummary,
    syncHybridProgress,
    syncHybridForecast,
    syncHybridBreakdown,
    syncHybridOverview,
    syncHistory,
    syncHistoryError,
    refreshSyncHistory,
    exportSyncHistory,
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

  const handleManualConflictResolution = useCallback(async () => {
    await handleResolveOutboxConflicts();
    await refreshOutbox();
    await refreshOutboxStats();
  }, [handleResolveOutboxConflicts, refreshOutbox, refreshOutboxStats]);

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

  const handleRetryEntry = useCallback(
    async (entryId: number) => {
      const reason = ensureReason(
        typeof window === "undefined"
          ? "Reintento manual desde panel"
          : window.prompt("Motivo para reintentar el evento", "Reintento manual desde panel"),
      );
      if (!reason) {
        pushToast({ message: "Indica un motivo corporativo para reintentar.", variant: "warning" });
        return;
      }
      try {
        await retrySyncOutbox(token ?? "", [entryId], reason);
        pushToast({ message: "Evento reagendado", variant: "success" });
        await refreshOutbox();
        await refreshOutboxStats();
      } catch (error) {
        const message = error instanceof Error ? error.message : "No se pudo reintentar el evento";
        pushToast({ message, variant: "error" });
      }
    },
    [pushToast, refreshOutbox, refreshOutboxStats, token],
  );

  const handlePriorityChange = useCallback(
    async (entryId: number, priority: "HIGH" | "NORMAL" | "LOW") => {
      const reason = ensureReason(
        typeof window === "undefined"
          ? "Ajuste de prioridad desde panel"
          : window.prompt("Motivo para ajustar la prioridad", "Ajuste de prioridad desde panel"),
      );
      if (!reason) {
        pushToast({ message: "Ingresa un motivo válido para priorizar el evento.", variant: "warning" });
        return;
      }
      await reprioritizeOutbox(entryId, priority, reason);
      await refreshOutbox();
      await refreshOutboxStats();
    },
    [pushToast, refreshOutbox, refreshOutboxStats, reprioritizeOutbox],
  );

  const handleExportHistory = useCallback(async () => {
    const reason = ensureReason(
      typeof window === "undefined"
        ? "Exportación historial sincronización"
        : window.prompt("Motivo para exportar historial", "Exportación historial sincronización"),
    );
    if (!reason) {
      pushToast({ message: "Debes indicar un motivo corporativo para exportar.", variant: "warning" });
      return;
    }
    await exportSyncHistory(reason);
  }, [exportSyncHistory, pushToast]);

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
          conflictCount={outboxConflicts}
          lastConflictAt={lastOutboxConflict}
          onResolveConflicts={handleManualConflictResolution}
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
          <div className="hybrid-queue__actions">
            <button type="button" className="btn btn-ghost" onClick={() => void refreshSyncHistory()}>
              Actualizar historial
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => void handleExportHistory()}>
              Exportar CSV
            </button>
          </div>
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
                      <span className="sync-log__time">Inicio: {new Date(session.started_at).toLocaleString("es-HN")}</span>
                      {session.finished_at ? (
                        <span className="sync-log__time">Fin: {new Date(session.finished_at).toLocaleString("es-HN")}</span>
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
              className="btn btn-warning"
              disabled={outboxConflicts === 0}
              onClick={() => void handleManualConflictResolution()}
            >
              Resolver conflictos
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
                  <th>Conflictos</th>
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
                    <td>{entry.conflicts}</td>
                    <td>{entry.latest_update ? new Date(entry.latest_update).toLocaleString("es-HN") : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="section-divider">
          <h3>Detalle de eventos</h3>
          {outbox.length === 0 ? (
            <p className="hybrid-queue__hint">No hay eventos individuales para mostrar.</p>
          ) : (
            <div className="card">
              <table className="outbox-table">
                <thead>
                  <tr>
                    <th>Entidad</th>
                    <th>Operación</th>
                    <th>Estado</th>
                    <th>Prioridad</th>
                    <th>Intentos</th>
                    <th>Latencia</th>
                    <th>Último intento</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {outbox.map((entry) => (
                    <tr key={entry.id}>
                      <td>{entry.entity_type}</td>
                      <td>{entry.operation}</td>
                      <td>
                        <span className="badge neutral">
                          {entry.status_detail?.replace("_", " ") ?? entry.status.toLowerCase()}
                        </span>
                        {entry.error_message ? (
                          <small className="sync-history-error">{entry.error_message}</small>
                        ) : null}
                      </td>
                      <td>
                        <select
                          value={entry.priority}
                          onChange={(event) =>
                            void handlePriorityChange(
                              entry.id,
                              event.target.value as "HIGH" | "NORMAL" | "LOW",
                            )
                          }
                        >
                          <option value="HIGH">Alta</option>
                          <option value="NORMAL">Normal</option>
                          <option value="LOW">Baja</option>
                        </select>
                      </td>
                      <td>{entry.attempt_count}</td>
                      <td>
                        <div className="sync-latency">
                          <span>Total: {formatLatencyMs(entry.latency_ms)}</span>
                          <span>Proceso: {formatLatencyMs(entry.processing_latency_ms)}</span>
                        </div>
                      </td>
                      <td>
                        {entry.last_attempt_at
                          ? new Date(entry.last_attempt_at).toLocaleString("es-HN")
                          : "Sin intentos"}
                      </td>
                      <td>
                        <div className="hybrid-queue__actions">
                          <button
                            type="button"
                            className="btn btn-ghost"
                            onClick={() => void handleRetryEntry(entry.id)}
                          >
                            Reintentar
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
