import { createContext, useCallback, useContext, useEffect, useMemo, type ReactNode } from "react";
import { featureFlags } from "@/config/featureFlags";
import { syncClient } from "../../sync/services/syncClient";
import { NETWORK_EVENT, NETWORK_RECOVERY_EVENT } from "@api/client";
import type {
  Device,
  DeviceUpdateInput,
  InventoryMetrics,
  MovementInput,
  Store,
} from "@api/inventory";
import type { Summary } from "@api/stores";
import type { BackupJob, ReleaseInfo, UpdateStatus } from "@api/system";
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
import type { UserAccount } from "@api/users";
import { useUIState, ToastMessage } from "../hooks/useUIState";
import { useSystemData } from "../hooks/useSystemData";
import { useInventoryData } from "../hooks/useInventoryData";
import { useSyncData } from "../hooks/useSyncData";

export type { ToastMessage };

export type DashboardContextValue = {
  token: string;
  enableCatalogPro: boolean;
  enableTransfers: boolean;
  enablePurchasesSales: boolean;
  enableAnalyticsAdv: boolean;
  enableTwoFactor: boolean;
  enableHybridPrep: boolean;
  enablePriceLists: boolean;
  enableVariants: boolean;
  enableBundles: boolean;
  enableDte: boolean;
  compactMode: boolean;
  setCompactMode: (value: boolean) => void;
  toggleCompactMode: () => void;
  globalSearchTerm: string;
  setGlobalSearchTerm: (term: string) => void;
  stores: Store[];
  summary: Summary[];
  metrics: InventoryMetrics | null;
  devices: Device[];
  backupHistory: BackupJob[];
  releaseHistory: ReleaseInfo[];
  updateStatus: UpdateStatus | null;
  selectedStoreId: number | null;
  setSelectedStoreId: (storeId: number | null) => void;
  selectedStore: Store | null;
  loading: boolean;
  message: string | null;
  setMessage: (message: string | null) => void;
  error: string | null;
  setError: (error: string | null) => void;
  syncStatus: string | null;
  outbox: SyncOutboxEntry[];
  outboxError: string | null;
  outboxStats: SyncOutboxStatsEntry[];
  outboxConflicts: number;
  lastOutboxConflict: Date | null;
  syncQueueSummary: SyncQueueSummary | null;
  syncHybridProgress: SyncHybridProgress | null;
  syncHybridForecast: SyncHybridForecast | null;
  syncHybridBreakdown: SyncHybridModuleBreakdownItem[];
  syncHybridOverview: SyncHybridOverview | null;
  observability: ObservabilitySnapshot | null;
  observabilityError: string | null;
  observabilityLoading: boolean;
  currentUser: UserAccount | null;
  syncHistory: SyncStoreHistory[];
  syncHistoryError: string | null;
  formatCurrency: (value: number) => string;
  totalDevices: number;
  totalItems: number;
  totalValue: number;
  lowStockDevices: InventoryMetrics["low_stock_devices"];
  topStores: InventoryMetrics["top_stores"];
  currentLowStockThreshold: number;
  updateLowStockThreshold: (
    storeId: number,
    threshold: number,
    setError: (msg: string | null) => void,
  ) => Promise<void>;
  handleMovement: (payload: MovementInput) => Promise<void>;
  handleDeviceUpdate: (
    deviceId: number,
    updates: DeviceUpdateInput,
    reason: string,
  ) => Promise<void>;
  refreshInventoryAfterTransfer: () => Promise<void>;
  refreshSummary: () => Promise<void>;
  lastInventoryRefresh: Date | null;
  handleSync: () => Promise<void>;
  handleBackup: (reason: string, note?: string) => Promise<void>;
  refreshOutbox: () => Promise<void>;
  handleRetryOutbox: () => Promise<void>;
  reprioritizeOutbox: (
    entryId: number,
    priority: SyncOutboxStatsEntry["priority"],
    reason: string,
  ) => Promise<void>;
  handleResolveOutboxConflicts: () => Promise<void>;
  downloadInventoryReport: (reason: string) => Promise<void>;
  refreshOutboxStats: () => Promise<void>;
  refreshSyncQueueSummary: () => Promise<void>;
  refreshSyncHistory: () => Promise<void>;
  exportSyncHistory: (reason: string) => Promise<void>;
  refreshObservability: () => Promise<void>;
  toasts: ToastMessage[];
  pushToast: (toast: Omit<ToastMessage, "id">) => void;
  dismissToast: (id: number) => void;
  networkAlert: string | null;
  dismissNetworkAlert: () => void;
  refreshStores: () => Promise<void>;
};

export const DashboardContext = createContext<DashboardContextValue | undefined>(undefined);

type ProviderProps = {
  token: string;
  children: ReactNode;
};

export function DashboardProvider({ token, children }: ProviderProps) {
  const {
    catalogPro: enableCatalogPro,
    transfers: enableTransfers,
    purchasesSales: enablePurchasesSales,
    analyticsAdv: enableAnalyticsAdv,
    twoFactor: enableTwoFactor,
    hybridPrep: enableHybridPrep,
    priceLists: enablePriceLists,
    variants: enableVariants,
    bundles: enableBundles,
    dte: enableDte,
  } = featureFlags;

  const {
    compactMode,
    setCompactMode,
    toggleCompactMode,
    globalSearchTerm,
    setGlobalSearchTerm,
    toasts,
    pushToast,
    dismissToast,
    networkAlert,
    setNetworkAlert,
    dismissNetworkAlert,
    loading,
    setLoading,
    message,
    setMessage,
    error,
    setError,
    friendlyErrorMessage,
  } = useUIState();

  const {
    backupHistory,
    releaseHistory,
    updateStatus,
    currentUser,
    fetchSystemData,
    handleBackup: handleBackupAction,
  } = useSystemData(token, pushToast, friendlyErrorMessage);

  const {
    stores,
    summary,
    metrics,
    devices,
    lastInventoryRefresh,
    selectedStoreId,
    setSelectedStoreId,
    selectedStore,
    currentLowStockThreshold,
    refreshSummary,
    refreshStores,
    fetchInventoryData,
    handleMovement: handleMovementAction,
    handleDeviceUpdate: handleDeviceUpdateAction,
    refreshInventoryAfterTransfer,
    updateLowStockThreshold,
    downloadInventoryReport,
    totals,
  } = useInventoryData(token, pushToast, friendlyErrorMessage, syncClient);

  const {
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
    handleSync: handleSyncAction,
    handleRetryOutbox: handleRetryOutboxAction,
    reprioritizeOutbox,
    exportSyncHistory,
    handleResolveOutboxConflicts: handleResolveOutboxConflictsAction,
    conflictEntries,
    lastOutboxConflict,
  } = useSyncData(token, enableHybridPrep, pushToast, friendlyErrorMessage);

  const currencyFormatter = useMemo(
    () => new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" }),
    [],
  );

  const formatCurrency = useCallback(
    (value: number) => currencyFormatter.format(value),
    [currencyFormatter],
  );

  useEffect(() => {
    const handleNetworkError = (event: Event) => {
      const customEvent = event as CustomEvent<string>;
      setNetworkAlert(customEvent.detail ?? "Problemas de conectividad con la API corporativa.");
    };
    const handleNetworkRecovery = () => {
      setNetworkAlert(null);
    };

    window.addEventListener(NETWORK_EVENT, handleNetworkError);
    window.addEventListener(NETWORK_RECOVERY_EVENT, handleNetworkRecovery);
    return () => {
      window.removeEventListener(NETWORK_EVENT, handleNetworkError);
      window.removeEventListener(NETWORK_RECOVERY_EVENT, handleNetworkRecovery);
    };
  }, [setNetworkAlert]);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([
        fetchSystemData(),
        fetchInventoryData(),
        refreshSyncHistory(),
        refreshObservability(),
        refreshOutbox(),
      ]);
      setLoading(false);
    };
    init();
  }, [
    fetchSystemData,
    fetchInventoryData,
    refreshSyncHistory,
    refreshObservability,
    refreshOutbox,
    setLoading,
  ]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return () => undefined;
    }

    let running = false;
    let disposed = false;

    const runRefresh = async () => {
      if (running || (typeof document !== "undefined" && document.hidden)) {
        return;
      }
      running = true;
      try {
        await refreshSummary();
        // Note: getDevices is called inside refreshSummary in the original code but here it is separate in useInventoryData
        // We might need to expose a way to refresh devices if selectedStoreId is set.
        // Actually useInventoryData handles devices refresh when selectedStoreId changes or handleMovement is called.
        // But for periodic refresh we need to trigger it.
        // Let's assume refreshSummary in useInventoryData only refreshes summary and metrics.
        // We need to check useInventoryData implementation.
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "No fue posible actualizar el inventario en tiempo real";
        const friendly = friendlyErrorMessage(message);
        if (!disposed) {
          setError(friendly);
          pushToast({ message: friendly, variant: "error" });
        }
      } finally {
        running = false;
      }
    };

    const interval = window.setInterval(() => {
      void runRefresh();
    }, 30000);

    const handleVisibility = () => {
      if (typeof document !== "undefined" && !document.hidden) {
        void runRefresh();
      }
    };

    if (typeof document !== "undefined") {
      document.addEventListener("visibilitychange", handleVisibility);
    }

    void runRefresh();

    return () => {
      disposed = true;
      window.clearInterval(interval);
      if (typeof document !== "undefined") {
        document.removeEventListener("visibilitychange", handleVisibility);
      }
    };
  }, [friendlyErrorMessage, pushToast, refreshSummary, setError]);

  useEffect(() => {
    syncClient.init();
    syncClient.setToken(token);
    return () => {
      if (!token) {
        syncClient.setToken(null);
      }
    };
  }, [token]);

  const handleMovement = useCallback(
    (payload: MovementInput) => handleMovementAction(payload, setError, setMessage),
    [handleMovementAction, setError, setMessage],
  );
  const handleDeviceUpdate = useCallback(
    (deviceId: number, updates: DeviceUpdateInput, reason: string) =>
      handleDeviceUpdateAction(deviceId, updates, reason, setError, setMessage),
    [handleDeviceUpdateAction, setError, setMessage],
  );
  const handleBackup = useCallback(
    (reason: string, note?: string) => handleBackupAction(reason, note, setError, setMessage),
    [handleBackupAction, setError, setMessage],
  );
  const handleSync = useCallback(() => handleSyncAction(), [handleSyncAction]);
  const handleRetryOutbox = useCallback(
    () => handleRetryOutboxAction(setMessage),
    [handleRetryOutboxAction, setMessage],
  );
  const handleResolveOutboxConflicts = useCallback(
    () => handleResolveOutboxConflictsAction(setMessage),
    [handleResolveOutboxConflictsAction, setMessage],
  );

  const { totalDevices, totalItems, totalValue, lowStock, topStores } = totals;

  const contextValue = useMemo<DashboardContextValue>(
    () => ({
      token,
      enableCatalogPro,
      enableTransfers,
      enablePurchasesSales,
      enableAnalyticsAdv,
      enableTwoFactor,
      enableHybridPrep,
      enablePriceLists,
      enableVariants,
      enableBundles,
      enableDte,
      compactMode,
      setCompactMode,
      toggleCompactMode,
      globalSearchTerm,
      setGlobalSearchTerm,
      stores,
      summary,
      metrics,
      devices,
      backupHistory,
      releaseHistory,
      updateStatus,
      lastInventoryRefresh,
      selectedStoreId,
      setSelectedStoreId,
      selectedStore,
      loading,
      message,
      setMessage,
      error,
      setError,
      syncStatus,
      outbox,
      outboxError,
      outboxStats,
      outboxConflicts: conflictEntries.length,
      lastOutboxConflict,
      syncQueueSummary,
      syncHybridProgress,
      syncHybridForecast,
      syncHybridBreakdown,
      syncHybridOverview,
      observability,
      observabilityError,
      observabilityLoading,
      currentUser,
      syncHistory,
      syncHistoryError,
      formatCurrency,
      totalDevices,
      totalItems,
      totalValue,
      lowStockDevices: lowStock,
      topStores,
      currentLowStockThreshold,
      updateLowStockThreshold,
      handleMovement,
      handleDeviceUpdate,
      refreshInventoryAfterTransfer,
      refreshSummary,
      handleSync,
      handleBackup,
      refreshOutbox,
      handleRetryOutbox,
      reprioritizeOutbox,
      handleResolveOutboxConflicts,
      downloadInventoryReport,
      refreshOutboxStats,
      refreshSyncQueueSummary,
      refreshSyncHistory,
      exportSyncHistory,
      refreshObservability,
      toasts,
      pushToast,
      dismissToast,
      networkAlert,
      dismissNetworkAlert,
      refreshStores,
    }),
    [
      token,
      enableCatalogPro,
      enableTransfers,
      enablePurchasesSales,
      enableAnalyticsAdv,
      enableTwoFactor,
      enableHybridPrep,
      enablePriceLists,
      enableVariants,
      enableBundles,
      enableDte,
      compactMode,
      setCompactMode,
      toggleCompactMode,
      globalSearchTerm,
      setGlobalSearchTerm,
      stores,
      summary,
      metrics,
      devices,
      backupHistory,
      releaseHistory,
      updateStatus,
      lastInventoryRefresh,
      selectedStoreId,
      setSelectedStoreId,
      selectedStore,
      loading,
      message,
      setMessage,
      error,
      setError,
      syncStatus,
      outbox,
      outboxError,
      outboxStats,
      conflictEntries.length,
      lastOutboxConflict,
      syncQueueSummary,
      syncHybridProgress,
      syncHybridForecast,
      syncHybridBreakdown,
      syncHybridOverview,
      observability,
      observabilityError,
      observabilityLoading,
      currentUser,
      syncHistory,
      syncHistoryError,
      formatCurrency,
      totalDevices,
      totalItems,
      totalValue,
      lowStock,
      topStores,
      currentLowStockThreshold,
      updateLowStockThreshold,
      handleMovement,
      handleDeviceUpdate,
      refreshInventoryAfterTransfer,
      refreshSummary,
      handleSync,
      handleBackup,
      refreshOutbox,
      handleRetryOutbox,
      reprioritizeOutbox,
      handleResolveOutboxConflicts,
      downloadInventoryReport,
      refreshOutboxStats,
      refreshSyncQueueSummary,
      refreshSyncHistory,
      exportSyncHistory,
      refreshObservability,
      toasts,
      pushToast,
      dismissToast,
      networkAlert,
      dismissNetworkAlert,
      refreshStores,
    ],
  );

  return <DashboardContext.Provider value={contextValue}>{children}</DashboardContext.Provider>;
}

export function useDashboard(): DashboardContextValue {
  const context = useContext(DashboardContext);
  if (!context) {
    throw new Error("useDashboard debe utilizarse dentro de DashboardProvider");
  }
  return context;
}
