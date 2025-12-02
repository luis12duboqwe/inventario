import { useState, useCallback, useMemo } from "react";
import {
  getSyncHistory,
  listSyncOutbox,
  retrySyncOutbox,
  updateSyncOutboxPriority,
  triggerSync,
  getSyncOutboxStats,
  getSyncQueueSummary,
  getSyncHybridProgress,
  getSyncHybridForecast,
  getSyncHybridBreakdown,
  getSyncHybridOverview,
  getObservabilitySnapshot,
  downloadSyncHistoryCsv,
  resolveSyncOutboxConflicts,
} from "@api/sync";
import { safeArray } from "../../../utils/safeValues";
import type {
  SyncOutboxEntry,
  SyncOutboxStatsEntry,
  SyncQueueSummary,
  SyncHybridProgress,
  SyncHybridForecast,
  SyncHybridModuleBreakdownItem,
  SyncHybridOverview,
  SyncStoreHistory,
  ObservabilitySnapshot,
} from "@api/sync";
import type { ToastMessage } from "../hooks/useUIState";

export function useSyncData(
  token: string,
  enableHybridPrep: boolean,
  pushToast: (toast: Omit<ToastMessage, "id">) => void,
  friendlyErrorMessage: (msg: string) => string
) {
  const [syncStatus, setSyncStatus] = useState<string | null>(null);
  const [outbox, setOutbox] = useState<SyncOutboxEntry[]>([]);
  const [outboxError, setOutboxError] = useState<string | null>(null);
  const [outboxStats, setOutboxStats] = useState<SyncOutboxStatsEntry[]>([]);
  const [syncQueueSummary, setSyncQueueSummary] = useState<SyncQueueSummary | null>(null);
  const [syncHybridProgress, setSyncHybridProgress] = useState<SyncHybridProgress | null>(null);
  const [syncHybridForecast, setSyncHybridForecast] = useState<SyncHybridForecast | null>(null);
  const [syncHybridBreakdown, setSyncHybridBreakdown] = useState<SyncHybridModuleBreakdownItem[]>([]);
  const [syncHybridOverview, setSyncHybridOverview] = useState<SyncHybridOverview | null>(null);
  const [observability, setObservability] = useState<ObservabilitySnapshot | null>(null);
  const [observabilityError, setObservabilityError] = useState<string | null>(null);
  const [observabilityLoading, setObservabilityLoading] = useState(false);
  const [syncHistory, setSyncHistory] = useState<SyncStoreHistory[]>([]);
  const [syncHistoryError, setSyncHistoryError] = useState<string | null>(null);

  const refreshObservability = useCallback(async () => {
    setObservabilityLoading(true);
    try {
      const snapshot = await getObservabilitySnapshot(token);
      setObservability(snapshot);
      setObservabilityError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "No se pudo consultar el estado de observabilidad";
      setObservabilityError(friendlyErrorMessage(message));
    } finally {
      setObservabilityLoading(false);
    }
  }, [friendlyErrorMessage, token]);

  const refreshSyncHistory = useCallback(async () => {
    try {
      const historyData = await getSyncHistory(token);
      setSyncHistory(safeArray(historyData));
      setSyncHistoryError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "No se pudo actualizar el historial de sincronización";
      setSyncHistoryError(friendlyErrorMessage(message));
    }
  }, [friendlyErrorMessage, token]);

  const refreshOutbox = useCallback(async () => {
    if (!enableHybridPrep) {
      setOutbox([]);
      setOutboxStats([]);
      setSyncQueueSummary(null);
      setSyncHybridProgress(null);
      setSyncHybridForecast(null);
      setSyncHybridBreakdown([]);
      setSyncHybridOverview(null);
      return;
    }
    try {
      const [entries, statsData, summaryData, overviewData] = await Promise.all([
        listSyncOutbox(token),
        getSyncOutboxStats(token),
        getSyncQueueSummary(token),
        getSyncHybridOverview(token),
      ]);
      setOutbox(entries);
      setOutboxStats(statsData);
      const normalizedSummary = overviewData.queue_summary ?? summaryData;
      setSyncQueueSummary(normalizedSummary);
      setSyncHybridOverview(overviewData);
      setSyncHybridForecast(overviewData.forecast);
      setSyncHybridProgress(overviewData.progress);
      setSyncHybridBreakdown(overviewData.breakdown);
      return;
    } catch {
      // Fallback
    }
    try {
      const [entries, statsData, summaryData, forecastData, breakdownData] = await Promise.all([
        listSyncOutbox(token),
        getSyncOutboxStats(token),
        getSyncQueueSummary(token),
        getSyncHybridForecast(token),
        getSyncHybridBreakdown(token),
      ]);
      setOutbox(entries);
      setOutboxStats(statsData);
      setSyncQueueSummary(summaryData);
      setSyncHybridForecast(forecastData);
      setSyncHybridProgress(forecastData.progress);
      setSyncHybridBreakdown(breakdownData);
      setOutboxError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "No se pudo consultar la cola de sincronización";
      const friendly = friendlyErrorMessage(message);
      setOutboxError(friendly);
      pushToast({ message: friendly, variant: "error" });
      setSyncHybridForecast(null);
      setSyncHybridBreakdown([]);
      setSyncHybridOverview(null);
      try {
        const fallback = await getSyncHybridProgress(token);
        setSyncHybridProgress(fallback);
      } catch {
        setSyncHybridProgress(null);
      }
    }
  }, [enableHybridPrep, friendlyErrorMessage, pushToast, token]);

  const refreshOutboxStats = useCallback(async () => {
    if (!enableHybridPrep) {
      setOutboxStats([]);
      setSyncQueueSummary(null);
      setSyncHybridProgress(null);
      setSyncHybridForecast(null);
      setSyncHybridBreakdown([]);
      setSyncHybridOverview(null);
      return;
    }
    try {
      const [statsData, summaryData, overviewData] = await Promise.all([
        getSyncOutboxStats(token),
        getSyncQueueSummary(token),
        getSyncHybridOverview(token),
      ]);
      setOutboxStats(statsData);
      const normalizedSummary = overviewData.queue_summary ?? summaryData;
      setSyncQueueSummary(normalizedSummary);
      setSyncHybridOverview(overviewData);
      setSyncHybridForecast(overviewData.forecast);
      setSyncHybridProgress(overviewData.progress);
      setSyncHybridBreakdown(overviewData.breakdown);
      return;
    } catch {
      // Fallback
    }
    try {
      const [statsData, summaryData, forecastData, breakdownData] = await Promise.all([
        getSyncOutboxStats(token),
        getSyncQueueSummary(token),
        getSyncHybridForecast(token),
        getSyncHybridBreakdown(token),
      ]);
      setOutboxStats(statsData);
      setSyncQueueSummary(summaryData);
      setSyncHybridForecast(forecastData);
      setSyncHybridProgress(forecastData.progress);
      setSyncHybridBreakdown(breakdownData);
    } catch (err) {
      const message = err instanceof Error ? err.message : "No se pudo consultar las estadísticas de la cola";
      setOutboxError(friendlyErrorMessage(message));
      setSyncHybridForecast(null);
      setSyncHybridBreakdown([]);
      setSyncHybridOverview(null);
      try {
        const fallback = await getSyncHybridProgress(token);
        setSyncHybridProgress(fallback);
      } catch {
        setSyncHybridProgress(null);
      }
    }
  }, [enableHybridPrep, friendlyErrorMessage, token]);

  const refreshSyncQueueSummary = useCallback(async () => {
    if (!enableHybridPrep) {
      setSyncQueueSummary(null);
      setSyncHybridProgress(null);
      setSyncHybridForecast(null);
      setSyncHybridBreakdown([]);
      setSyncHybridOverview(null);
      return;
    }
    try {
      const [summaryData, overviewData] = await Promise.all([
        getSyncQueueSummary(token),
        getSyncHybridOverview(token),
      ]);
      const normalizedSummary = overviewData.queue_summary ?? summaryData;
      setSyncQueueSummary(normalizedSummary);
      setSyncHybridOverview(overviewData);
      setSyncHybridForecast(overviewData.forecast);
      setSyncHybridProgress(overviewData.progress);
      setSyncHybridBreakdown(overviewData.breakdown);
      return;
    } catch {
      // Fallback
    }
    try {
      const [summaryData, forecastData, breakdownData] = await Promise.all([
        getSyncQueueSummary(token),
        getSyncHybridForecast(token),
        getSyncHybridBreakdown(token),
      ]);
      setSyncQueueSummary(summaryData);
      setSyncHybridForecast(forecastData);
      setSyncHybridProgress(forecastData.progress);
      setSyncHybridBreakdown(breakdownData);
    } catch (err) {
      const message = err instanceof Error ? err.message : "No se pudo consultar el progreso de la cola híbrida";
      setOutboxError(friendlyErrorMessage(message));
      setSyncHybridForecast(null);
      setSyncHybridBreakdown([]);
      setSyncHybridOverview(null);
      try {
        const fallback = await getSyncHybridProgress(token);
        setSyncHybridProgress(fallback);
      } catch {
        setSyncHybridProgress(null);
      }
    }
  }, [enableHybridPrep, friendlyErrorMessage, token]);

  const handleSync = useCallback(async () => {
    try {
      setSyncStatus("Sincronizando…");
      await triggerSync(token, "Sincronización manual desde dashboard");
      setSyncStatus("Sincronización completada");
      pushToast({ message: "Sincronización completada", variant: "success" });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Error durante la sincronización";
      const friendly = friendlyErrorMessage(message);
      setSyncStatus(friendly);
      pushToast({ message: friendly, variant: "error" });
    }
  }, [friendlyErrorMessage, pushToast, token]);

  const handleRetryOutbox = useCallback(async (setMessage: (msg: string | null) => void) => {
    if (!enableHybridPrep || outbox.length === 0) {
      return;
    }
    try {
      setOutboxError(null);
      const updated = await retrySyncOutbox(
        token,
        outbox.map((entry) => entry.id),
        "Reintento manual desde panel",
      );
      setOutbox(updated);
      setMessage("Eventos listos para reintento local");
      pushToast({ message: "Cola reagendada", variant: "success" });
      await refreshOutboxStats();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No se pudo reagendar la cola local";
      const friendly = friendlyErrorMessage(message);
      setOutboxError(friendly);
      pushToast({ message: friendly, variant: "error" });
    }
  }, [enableHybridPrep, friendlyErrorMessage, outbox, pushToast, refreshOutboxStats, token]);

  const reprioritizeOutbox = useCallback(
    async (entryId: number, priority: SyncOutboxStatsEntry["priority"], reason: string) => {
      if (!enableHybridPrep) {
        return;
      }
      try {
        const updated = await updateSyncOutboxPriority(token, entryId, priority, reason);
        setOutbox((current) => current.map((item) => (item.id === updated.id ? updated : item)));
        pushToast({ message: "Prioridad actualizada", variant: "success" });
        await refreshOutboxStats();
      } catch (err) {
        const message = err instanceof Error ? err.message : "No se pudo actualizar la prioridad";
        const friendly = friendlyErrorMessage(message);
        setOutboxError(friendly);
        pushToast({ message: friendly, variant: "error" });
      }
    },
    [enableHybridPrep, friendlyErrorMessage, pushToast, refreshOutboxStats, token]
  );

  const exportSyncHistory = useCallback(
    async (reason: string) => {
      if (!reason || reason.trim().length < 5) {
        pushToast({
          message: "Indica un motivo corporativo para la exportación.",
          variant: "warning",
        });
        return;
      }
      try {
        await downloadSyncHistoryCsv(token, reason.trim());
        pushToast({ message: "Historial exportado", variant: "success" });
      } catch (error) {
        const message = error instanceof Error ? error.message : "No fue posible exportar el historial";
        pushToast({ message, variant: "error" });
      }
    },
    [pushToast, token]
  );

  const conflictEntries = useMemo(() => outbox.filter((entry) => entry.conflict_flag), [outbox]);

  const lastOutboxConflict = useMemo<Date | null>(() => {
    if (conflictEntries.length === 0) {
      return null;
    }
    const timestamps = conflictEntries
      .map((entry) => new Date(entry.updated_at))
      .filter((date) => !Number.isNaN(date.getTime()));
    if (timestamps.length === 0) {
      return null;
    }
    return timestamps.sort((a, b) => b.getTime() - a.getTime())[0] ?? null;
  }, [conflictEntries]);

  const handleResolveOutboxConflicts = useCallback(async (setMessage: (msg: string | null) => void) => {
    if (!enableHybridPrep || conflictEntries.length === 0) {
      return;
    }
    const reason =
      typeof window === "undefined"
        ? "Resolución manual de conflictos outbox"
        : window.prompt(
            "Motivo corporativo para resolver conflictos",
            "Resolución manual de conflictos outbox",
          );
    if (!reason || reason.trim().length < 5) {
      pushToast({
        message: "Indica un motivo corporativo de al menos 5 caracteres para continuar.",
        variant: "warning",
      });
      return;
    }
    try {
      const updated = await resolveSyncOutboxConflicts(
        token,
        conflictEntries.map((entry) => entry.id),
        reason,
      );
      setOutbox(updated);
      setMessage("Conflictos marcados como resueltos");
      pushToast({
        message: `${updated.length} conflicto(s) listos para sincronización prioritizada`,
        variant: "success",
      });
      await refreshOutboxStats();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No se pudo resolver la cola con conflictos";
      const friendly = friendlyErrorMessage(message);
      setOutboxError(friendly);
      pushToast({ message: friendly, variant: "error" });
    }
  }, [
    conflictEntries,
    enableHybridPrep,
    friendlyErrorMessage,
    pushToast,
    refreshOutboxStats,
    token,
  ]);

  return {
    syncStatus,
    outbox,
    outboxError,
    outboxStats,
    syncQueueSummary,
    syncHybridProgress,
    syncHybridForecast,
    syncHybridBreakdown,
    syncHybridOverview,
    observability,
    observabilityError,
    observabilityLoading,
    syncHistory,
    syncHistoryError,
    refreshObservability,
    refreshSyncHistory,
    refreshOutbox,
    refreshOutboxStats,
    refreshSyncQueueSummary,
    handleSync,
    handleRetryOutbox,
    reprioritizeOutbox,
    exportSyncHistory,
    handleResolveOutboxConflicts,
    conflictEntries,
    lastOutboxConflict,
  };
}
