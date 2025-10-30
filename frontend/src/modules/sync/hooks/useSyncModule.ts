import { useDashboard } from "../../dashboard/context/DashboardContext";

export function useSyncModule() {
  const dashboard = useDashboard();

  return {
    handleSync: dashboard.handleSync,
    handleBackup: dashboard.handleBackup,
    downloadInventoryReport: dashboard.downloadInventoryReport,
    syncStatus: dashboard.syncStatus,
    backupHistory: dashboard.backupHistory,
    releaseHistory: dashboard.releaseHistory,
    updateStatus: dashboard.updateStatus,
    enableHybridPrep: dashboard.enableHybridPrep,
    outbox: dashboard.outbox,
    outboxError: dashboard.outboxError,
    refreshOutbox: dashboard.refreshOutbox,
    handleRetryOutbox: dashboard.handleRetryOutbox,
    outboxStats: dashboard.outboxStats,
    syncQueueSummary: dashboard.syncQueueSummary,
    syncHybridProgress: dashboard.syncHybridProgress,
    syncHybridForecast: dashboard.syncHybridForecast,
    syncHybridBreakdown: dashboard.syncHybridBreakdown,
    syncHistory: dashboard.syncHistory,
    syncHistoryError: dashboard.syncHistoryError,
    refreshSyncHistory: dashboard.refreshSyncHistory,
    refreshSyncQueueSummary: dashboard.refreshSyncQueueSummary,
    token: dashboard.token,
    stores: dashboard.stores,
    enableTransfers: dashboard.enableTransfers,
    pushToast: dashboard.pushToast,
    setError: dashboard.setError,
    setMessage: dashboard.setMessage,
    selectedStoreId: dashboard.selectedStoreId,
    selectedStore: dashboard.selectedStore,
    formatCurrency: dashboard.formatCurrency,
  };
}
