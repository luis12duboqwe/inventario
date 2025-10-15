import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  NETWORK_EVENT,
  NETWORK_RECOVERY_EVENT,
  downloadInventoryPdf,
  fetchBackupHistory,
  getDevices,
  getCurrentUser,
  getInventoryMetrics,
  getReleaseHistory,
  getStores,
  getSummary,
  getSyncHistory,
  getUpdateStatus,
  listSyncOutbox,
  registerMovement,
  retrySyncOutbox,
  triggerSync,
  runBackup,
  getSyncOutboxStats,
} from "../../../api";
import type {
  BackupJob,
  Device,
  UserAccount,
  InventoryMetrics,
  MovementInput,
  ReleaseInfo,
  Store,
  Summary,
  SyncOutboxEntry,
  SyncOutboxStatsEntry,
  SyncStoreHistory,
  UpdateStatus,
} from "../../../api";

type DashboardContextValue = {
  token: string;
  enableCatalogPro: boolean;
  enableTransfers: boolean;
  enablePurchasesSales: boolean;
  enableAnalyticsAdv: boolean;
  enableTwoFactor: boolean;
  enableHybridPrep: boolean;
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
  currentUser: UserAccount | null;
  syncHistory: SyncStoreHistory[];
  syncHistoryError: string | null;
  formatCurrency: (value: number) => string;
  totalDevices: number;
  totalItems: number;
  totalValue: number;
  lowStockDevices: InventoryMetrics["low_stock_devices"];
  topStores: InventoryMetrics["top_stores"];
  handleMovement: (payload: MovementInput) => Promise<void>;
  refreshInventoryAfterTransfer: () => Promise<void>;
  refreshSummary: () => Promise<void>;
  lastInventoryRefresh: Date | null;
  handleSync: () => Promise<void>;
  handleBackup: () => Promise<void>;
  refreshOutbox: () => Promise<void>;
  handleRetryOutbox: () => Promise<void>;
  downloadInventoryReport: () => Promise<void>;
  refreshOutboxStats: () => Promise<void>;
  refreshSyncHistory: () => Promise<void>;
  toasts: ToastMessage[];
  pushToast: (toast: Omit<ToastMessage, "id">) => void;
  dismissToast: (id: number) => void;
  networkAlert: string | null;
  dismissNetworkAlert: () => void;
};

const DashboardContext = createContext<DashboardContextValue | undefined>(undefined);

type ProviderProps = {
  token: string;
  children: ReactNode;
};

type ToastVariant = "success" | "error" | "info";

export type ToastMessage = {
  id: number;
  message: string;
  variant: ToastVariant;
};

export function DashboardProvider({ token, children }: ProviderProps) {
  const enableCatalogPro =
    (import.meta.env.VITE_SOFTMOBILE_ENABLE_CATALOG_PRO ?? "1") !== "0";
  const enableTransfers =
    (import.meta.env.VITE_SOFTMOBILE_ENABLE_TRANSFERS ?? "1") !== "0";
  const enablePurchasesSales =
    (import.meta.env.VITE_SOFTMOBILE_ENABLE_PURCHASES_SALES ?? "1") !== "0";
  const enableAnalyticsAdv =
    (import.meta.env.VITE_SOFTMOBILE_ENABLE_ANALYTICS_ADV ?? "1") !== "0";
  const enableTwoFactor =
    (import.meta.env.VITE_SOFTMOBILE_ENABLE_2FA ?? "0") !== "0";
  const enableHybridPrep =
    (import.meta.env.VITE_SOFTMOBILE_ENABLE_HYBRID_PREP ?? "1") !== "0";

  const [stores, setStores] = useState<Store[]>([]);
  const [summary, setSummary] = useState<Summary[]>([]);
  const [metrics, setMetrics] = useState<InventoryMetrics | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [lastInventoryRefresh, setLastInventoryRefresh] = useState<Date | null>(null);
  const [backupHistory, setBackupHistory] = useState<BackupJob[]>([]);
  const [releaseHistory, setReleaseHistory] = useState<ReleaseInfo[]>([]);
  const [updateStatus, setUpdateStatus] = useState<UpdateStatus | null>(null);
  const [currentUser, setCurrentUser] = useState<UserAccount | null>(null);
  const [selectedStoreId, setSelectedStoreId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<string | null>(null);
  const [outbox, setOutbox] = useState<SyncOutboxEntry[]>([]);
  const [outboxError, setOutboxError] = useState<string | null>(null);
  const [outboxStats, setOutboxStats] = useState<SyncOutboxStatsEntry[]>([]);
  const [syncHistory, setSyncHistory] = useState<SyncStoreHistory[]>([]);
  const [syncHistoryError, setSyncHistoryError] = useState<string | null>(null);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [networkAlert, setNetworkAlert] = useState<string | null>(null);

  const currencyFormatter = useMemo(
    () => new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }),
    []
  );

  const pushToast = useCallback((toast: Omit<ToastMessage, "id">) => {
    const id = Date.now() + Math.round(Math.random() * 1000);
    setToasts((current) => [...current, { id, ...toast }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((entry) => entry.id !== id));
    }, 4500);
  }, []);

  const dismissToast = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

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
  }, []);

  const formatCurrency = (value: number) => currencyFormatter.format(value);

  const selectedStore = useMemo(
    () => stores.find((store) => store.id === selectedStoreId) ?? null,
    [stores, selectedStoreId]
  );

  useEffect(() => {
    const fetchInitial = async () => {
      try {
        setLoading(true);
        const [storesData, summaryData, metricsData, backupData, statusData, releasesData] = await Promise.all([
          getStores(token),
          getSummary(token),
          getInventoryMetrics(token),
          fetchBackupHistory(token),
          getUpdateStatus(token),
          getReleaseHistory(token),
        ]);
        setStores(storesData);
        setSummary(summaryData);
        setMetrics(metricsData);
        setBackupHistory(backupData);
        setUpdateStatus(statusData);
        setReleaseHistory(releasesData);
        try {
          const userData = await getCurrentUser(token);
          setCurrentUser(userData);
        } catch (userErr) {
          const message =
            userErr instanceof Error
              ? userErr.message
              : "No fue posible obtener el usuario actual";
          setCurrentUser(null);
          pushToast({ message, variant: "error" });
        }
        try {
          const historyData = await getSyncHistory(token);
          setSyncHistory(historyData);
          setSyncHistoryError(null);
        } catch (historyErr) {
          setSyncHistory([]);
          setSyncHistoryError(
            historyErr instanceof Error
              ? historyErr.message
              : "No fue posible consultar el historial de sincronización",
          );
        }
        if (storesData.length > 0) {
          const firstStoreId = storesData[0].id;
          setSelectedStoreId(firstStoreId);
          const devicesData = await getDevices(token, firstStoreId);
          setDevices(devicesData);
          setLastInventoryRefresh(new Date());
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible cargar los datos iniciales");
      } finally {
        setLoading(false);
      }
    };

    fetchInitial();
  }, [token, pushToast]);

  useEffect(() => {
    const loadDevices = async () => {
      if (!selectedStoreId) {
        setDevices([]);
        return;
      }
      try {
        const devicesData = await getDevices(token, selectedStoreId);
        setDevices(devicesData);
        setLastInventoryRefresh(new Date());
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible cargar los dispositivos");
      }
    };

    loadDevices();
  }, [selectedStoreId, token]);

  useEffect(() => {
    const loadOutbox = async () => {
      if (!enableHybridPrep) {
        setOutbox([]);
        setOutboxStats([]);
        return;
      }
      try {
        const [entries, statsData] = await Promise.all([
          listSyncOutbox(token),
          getSyncOutboxStats(token),
        ]);
        setOutbox(entries);
        setOutboxStats(statsData);
        setOutboxError(null);
      } catch (err) {
        setOutboxError(err instanceof Error ? err.message : "No fue posible consultar la cola de sincronización");
      }
    };

    loadOutbox();
  }, [enableHybridPrep, token]);

  const refreshSummary = useCallback(async () => {
    const [summaryData, metricsData] = await Promise.all([
      getSummary(token),
      getInventoryMetrics(token),
    ]);
    setSummary(summaryData);
    setMetrics(metricsData);
  }, [token]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      void (async () => {
        try {
          await refreshSummary();
          if (selectedStoreId) {
            const refreshedDevices = await getDevices(token, selectedStoreId);
            setDevices(refreshedDevices);
            setLastInventoryRefresh(new Date());
          }
        } catch (err) {
          setError(
            err instanceof Error
              ? err.message
              : "No fue posible actualizar el inventario en tiempo real",
          );
        }
      })();
    }, 30000);

    return () => window.clearInterval(interval);
  }, [refreshSummary, selectedStoreId, token]);

  const handleMovement = async (payload: MovementInput) => {
    if (!selectedStoreId) {
      return;
    }
    const reason = payload.reason?.trim() ?? "";
    if (reason.length < 5) {
      setError("Indica un motivo corporativo de al menos 5 caracteres.");
      return;
    }
    try {
      setError(null);
      await registerMovement(token, selectedStoreId, payload, reason);
      setMessage("Movimiento registrado correctamente");
      pushToast({ message: "Movimiento registrado", variant: "success" });
      await Promise.all([
        refreshSummary(),
        getDevices(token, selectedStoreId).then(setDevices),
      ]);
      setLastInventoryRefresh(new Date());
    } catch (err) {
      const message = err instanceof Error ? err.message : "No se pudo registrar el movimiento";
      setError(message);
      pushToast({ message, variant: "error" });
    }
  };

  const refreshInventoryAfterTransfer = async () => {
    await refreshSummary();
    if (selectedStoreId) {
      const devicesData = await getDevices(token, selectedStoreId);
      setDevices(devicesData);
      setLastInventoryRefresh(new Date());
    }
  };

  const handleSync = async () => {
    try {
      setSyncStatus("Sincronizando…");
      await triggerSync(token, selectedStoreId ?? undefined);
      setSyncStatus("Sincronización completada");
      pushToast({ message: "Sincronización completada", variant: "success" });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Error durante la sincronización";
      setSyncStatus(message);
      pushToast({ message, variant: "error" });
    }
  };

  const handleBackup = async () => {
    try {
      setError(null);
      const job = await runBackup(token, "Respaldo manual desde tienda");
      setBackupHistory((current) => [job, ...current].slice(0, 10));
      setMessage("Respaldo generado y almacenado en el servidor central");
      pushToast({ message: "Respaldo generado", variant: "success" });
    } catch (err) {
      const message = err instanceof Error ? err.message : "No se pudo generar el respaldo";
      setError(message);
      pushToast({ message, variant: "error" });
    }
  };

  const refreshOutboxStats = useCallback(async () => {
    if (!enableHybridPrep) {
      setOutboxStats([]);
      return;
    }
    try {
      const statsData = await getSyncOutboxStats(token);
      setOutboxStats(statsData);
    } catch (err) {
      setOutboxError(err instanceof Error ? err.message : "No se pudo consultar las estadísticas de la cola");
    }
  }, [enableHybridPrep, token]);

  const refreshSyncHistory = useCallback(async () => {
    try {
      const historyData = await getSyncHistory(token);
      setSyncHistory(historyData);
      setSyncHistoryError(null);
    } catch (err) {
      setSyncHistoryError(
        err instanceof Error ? err.message : "No se pudo actualizar el historial de sincronización",
      );
    }
  }, [token]);

  const refreshOutbox = async () => {
    if (!enableHybridPrep) {
      setOutbox([]);
      setOutboxStats([]);
      return;
    }
    try {
      const [entries, statsData] = await Promise.all([
        listSyncOutbox(token),
        getSyncOutboxStats(token),
      ]);
      setOutbox(entries);
      setOutboxStats(statsData);
      setOutboxError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "No se pudo actualizar la cola local";
      setOutboxError(message);
      pushToast({ message, variant: "error" });
    }
  };

  const handleRetryOutbox = async () => {
    if (!enableHybridPrep || outbox.length === 0) {
      return;
    }
    try {
      setOutboxError(null);
      const updated = await retrySyncOutbox(
        token,
        outbox.map((entry) => entry.id),
        "Reintento manual desde panel"
      );
      setOutbox(updated);
      setMessage("Eventos listos para reintento local");
      pushToast({ message: "Cola reagendada", variant: "success" });
      await refreshOutboxStats();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No se pudo reagendar la cola local";
      setOutboxError(message);
      pushToast({ message, variant: "error" });
    }
  };

  const totals = useMemo(() => {
    const totalDevices =
      metrics?.totals.devices ?? summary.reduce((acc, store) => acc + store.devices.length, 0);
    const totalItems =
      metrics?.totals.total_units ?? summary.reduce((acc, store) => acc + store.total_items, 0);
    const totalValue =
      metrics?.totals.total_value ??
      summary.reduce(
        (acc, store) =>
          acc + store.devices.reduce((deviceAcc, device) => deviceAcc + device.inventory_value, 0),
        0
      );

    const lowStock = metrics?.low_stock_devices ?? [];
    const topStores = metrics?.top_stores ?? [];

    return { totalDevices, totalItems, totalValue, lowStock, topStores };
  }, [metrics, summary]);

  const downloadInventoryReport = async () => {
    await downloadInventoryPdf(token);
  };

  const value: DashboardContextValue = {
    token,
    enableCatalogPro,
    enableTransfers,
    enablePurchasesSales,
    enableAnalyticsAdv,
    enableTwoFactor,
    enableHybridPrep,
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
    currentUser,
    syncHistory,
    syncHistoryError,
    formatCurrency,
    totalDevices: totals.totalDevices,
    totalItems: totals.totalItems,
    totalValue: totals.totalValue,
    lowStockDevices: totals.lowStock,
    topStores: totals.topStores,
    handleMovement,
    refreshInventoryAfterTransfer,
    refreshSummary,
    handleSync,
    handleBackup,
    refreshOutbox,
    handleRetryOutbox,
    downloadInventoryReport,
    refreshOutboxStats,
    refreshSyncHistory,
    toasts,
    pushToast,
    dismissToast,
    networkAlert,
    dismissNetworkAlert: () => setNetworkAlert(null),
  };

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
}

export function useDashboard(): DashboardContextValue {
  const context = useContext(DashboardContext);
  if (!context) {
    throw new Error("useDashboard debe utilizarse dentro de DashboardProvider");
  }
  return context;
}

