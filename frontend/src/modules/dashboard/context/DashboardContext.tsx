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
  updateDevice,
} from "../../../api";
import type {
  BackupJob,
  Device,
  DeviceUpdateInput,
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
  updateLowStockThreshold: (storeId: number, threshold: number) => Promise<void>;
  handleMovement: (payload: MovementInput) => Promise<void>;
  handleDeviceUpdate: (deviceId: number, updates: DeviceUpdateInput, reason: string) => Promise<void>;
  refreshInventoryAfterTransfer: () => Promise<void>;
  refreshSummary: () => Promise<void>;
  lastInventoryRefresh: Date | null;
  handleSync: () => Promise<void>;
  handleBackup: () => Promise<void>;
  refreshOutbox: () => Promise<void>;
  handleRetryOutbox: () => Promise<void>;
  downloadInventoryReport: (reason: string) => Promise<void>;
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

const DEFAULT_LOW_STOCK_THRESHOLD = 5;

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

  const [compactModeState, setCompactModeState] = useState<boolean>(() => {
    if (typeof window === "undefined") {
      return false;
    }
    return window.localStorage.getItem("softmobile_compact_mode") === "1";
  });
  const [globalSearchTerm, setGlobalSearchTerm] = useState<string>("");
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
  const [lowStockThresholds, setLowStockThresholds] = useState<Record<number, number>>({});

  const currencyFormatter = useMemo(
    () => new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }),
    []
  );

  const persistCompactMode = (value: boolean) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem("softmobile_compact_mode", value ? "1" : "0");
    }
  };

  const setCompactMode = useCallback((value: boolean) => {
    setCompactModeState(value);
    persistCompactMode(value);
  }, []);

  const toggleCompactMode = useCallback(() => {
    setCompactModeState((current) => {
      const next = !current;
      persistCompactMode(next);
      return next;
    });
  }, []);

  const friendlyErrorMessage = useCallback((message: string) => {
    if (!message) {
      return "Ocurrió un error inesperado";
    }
    if (message.toLowerCase().includes("failed to fetch")) {
      return "No fue posible conectar con el servicio Softmobile. Verifica tu red e inténtalo nuevamente.";
    }
    return message;
  }, []);

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

  const dismissNetworkAlert = useCallback(() => {
    setNetworkAlert(null);
  }, []);

  const formatCurrency = useCallback((value: number) => currencyFormatter.format(value), [currencyFormatter]);

  const getThresholdForStore = useCallback(
    (storeId: number | null | undefined) => {
      if (!storeId) {
        return DEFAULT_LOW_STOCK_THRESHOLD;
      }
      return lowStockThresholds[storeId] ?? DEFAULT_LOW_STOCK_THRESHOLD;
    },
    [lowStockThresholds],
  );

  const selectedStore = useMemo(
    () => stores.find((store) => store.id === selectedStoreId) ?? null,
    [stores, selectedStoreId]
  );

  const currentLowStockThreshold = useMemo(
    () => getThresholdForStore(selectedStoreId),
    [getThresholdForStore, selectedStoreId],
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
        setLowStockThresholds((current) => {
          const next = { ...current };
          for (const store of storesData) {
            if (next[store.id] === undefined) {
              next[store.id] = DEFAULT_LOW_STOCK_THRESHOLD;
            }
          }
          return next;
        });
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
        const message = err instanceof Error ? err.message : "No fue posible cargar los datos iniciales";
        setError(friendlyErrorMessage(message));
      } finally {
        setLoading(false);
      }
    };

    fetchInitial();
  }, [token, pushToast]);

  useEffect(() => {
    if (stores.length === 0) {
      return;
    }
    const synchronizeMetrics = async () => {
      try {
        const metricsData = await getInventoryMetrics(token, currentLowStockThreshold);
        setMetrics(metricsData);
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "No fue posible obtener las métricas de inventario";
        setError(friendlyErrorMessage(message));
      }
    };

    void synchronizeMetrics();
  }, [currentLowStockThreshold, friendlyErrorMessage, stores.length, token]);

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
        const message = err instanceof Error ? err.message : "No fue posible cargar los dispositivos";
        setError(friendlyErrorMessage(message));
      }
    };

    loadDevices();
  }, [friendlyErrorMessage, selectedStoreId, token]);

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
        const message =
          err instanceof Error ? err.message : "No fue posible consultar la cola de sincronización";
        setOutboxError(friendlyErrorMessage(message));
      }
    };

    loadOutbox();
  }, [enableHybridPrep, friendlyErrorMessage, token]);

  const refreshSummary = useCallback(async () => {
    const threshold = getThresholdForStore(selectedStoreId);
    const [summaryData, metricsData] = await Promise.all([
      getSummary(token),
      getInventoryMetrics(token, threshold),
    ]);
    setSummary(summaryData);
    setMetrics(metricsData);
  }, [getThresholdForStore, selectedStoreId, token]);

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
          const message =
            err instanceof Error
              ? err.message
              : "No fue posible actualizar el inventario en tiempo real";
          setError(friendlyErrorMessage(message));
        }
      })();
    }, 30000);

    return () => window.clearInterval(interval);
  }, [friendlyErrorMessage, refreshSummary, selectedStoreId, token]);

  const handleMovement = async (payload: MovementInput) => {
    if (!selectedStoreId) {
      return;
    }
    const comment = payload.comentario.trim();
    if (comment.length < 5) {
      setError("Indica un motivo corporativo de al menos 5 caracteres.");
      return;
    }
    try {
      setError(null);
      await registerMovement(token, selectedStoreId, payload, comment);
      setMessage("Movimiento registrado correctamente");
      pushToast({ message: "Movimiento registrado", variant: "success" });
      await Promise.all([
        refreshSummary(),
        getDevices(token, selectedStoreId).then(setDevices),
      ]);
      setLastInventoryRefresh(new Date());
    } catch (err) {
      const message = err instanceof Error ? err.message : "No se pudo registrar el movimiento";
      const friendly = friendlyErrorMessage(message);
      setError(friendly);
      pushToast({ message: friendly, variant: "error" });
    }
  };

  const handleDeviceUpdate = async (
    deviceId: number,
    updates: DeviceUpdateInput,
    reason: string,
  ) => {
    if (!selectedStoreId) {
      return;
    }
    const normalizedReason = reason.trim();
    if (normalizedReason.length < 5) {
      setError("Indica un motivo corporativo de al menos 5 caracteres.");
      return;
    }
    if (Object.keys(updates).length === 0) {
      setError("No hay cambios por aplicar en el dispositivo seleccionado.");
      return;
    }
    try {
      setError(null);
      await updateDevice(token, selectedStoreId, deviceId, updates, normalizedReason);
      setMessage("Dispositivo actualizado correctamente");
      pushToast({ message: "Ficha de dispositivo actualizada", variant: "success" });
      await Promise.all([
        refreshSummary(),
        getDevices(token, selectedStoreId).then(setDevices),
      ]);
      setLastInventoryRefresh(new Date());
    } catch (err) {
      const message = err instanceof Error ? err.message : "No se pudo actualizar el dispositivo";
      const friendly = friendlyErrorMessage(message);
      setError(friendly);
      pushToast({ message: friendly, variant: "error" });
      throw new Error(friendly);
    }
  };

  const refreshInventoryAfterTransfer = useCallback(async () => {
    await refreshSummary();
    if (selectedStoreId) {
      const devicesData = await getDevices(token, selectedStoreId);
      setDevices(devicesData);
      setLastInventoryRefresh(new Date());
    }
  }, [refreshSummary, selectedStoreId, token]);

  const handleSync = useCallback(async () => {
    try {
      setSyncStatus("Sincronizando…");
      await triggerSync(token, selectedStoreId ?? undefined);
      setSyncStatus("Sincronización completada");
      pushToast({ message: "Sincronización completada", variant: "success" });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Error durante la sincronización";
      const friendly = friendlyErrorMessage(message);
      setSyncStatus(friendly);
      pushToast({ message: friendly, variant: "error" });
    }
  }, [friendlyErrorMessage, pushToast, selectedStoreId, token]);

  const handleBackup = useCallback(async () => {
    try {
      setError(null);
      const job = await runBackup(token, "Respaldo manual desde tienda");
      setBackupHistory((current) => [job, ...current].slice(0, 10));
      setMessage("Respaldo generado y almacenado en el servidor central");
      pushToast({ message: "Respaldo generado", variant: "success" });
    } catch (err) {
      const message = err instanceof Error ? err.message : "No se pudo generar el respaldo";
      const friendly = friendlyErrorMessage(message);
      setError(friendly);
      pushToast({ message: friendly, variant: "error" });
    }
  }, [friendlyErrorMessage, pushToast, token]);

  const refreshOutboxStats = useCallback(async () => {
    if (!enableHybridPrep) {
      setOutboxStats([]);
      return;
    }
    try {
      const statsData = await getSyncOutboxStats(token);
      setOutboxStats(statsData);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "No se pudo consultar las estadísticas de la cola";
      setOutboxError(friendlyErrorMessage(message));
    }
  }, [enableHybridPrep, friendlyErrorMessage, token]);

  const refreshSyncHistory = useCallback(async () => {
    try {
      const historyData = await getSyncHistory(token);
      setSyncHistory(historyData);
      setSyncHistoryError(null);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "No se pudo actualizar el historial de sincronización";
      setSyncHistoryError(friendlyErrorMessage(message));
    }
  }, [friendlyErrorMessage, token]);

  const refreshOutbox = useCallback(async () => {
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
      const friendly = friendlyErrorMessage(message);
      setOutboxError(friendly);
      pushToast({ message: friendly, variant: "error" });
    }
  }, [enableHybridPrep, friendlyErrorMessage, pushToast, token]);

  const handleRetryOutbox = useCallback(async () => {
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
      const friendly = friendlyErrorMessage(message);
      setOutboxError(friendly);
      pushToast({ message: friendly, variant: "error" });
    }
  }, [enableHybridPrep, friendlyErrorMessage, outbox, pushToast, refreshOutboxStats, token]);

  const updateLowStockThreshold = useCallback(
    async (storeId: number, threshold: number) => {
      const previous = getThresholdForStore(storeId);
      setLowStockThresholds((current) => ({ ...current, [storeId]: threshold }));
      if (selectedStoreId !== storeId) {
        return;
      }
      try {
        const metricsData = await getInventoryMetrics(token, threshold);
        setMetrics(metricsData);
      } catch (err) {
        setLowStockThresholds((current) => ({ ...current, [storeId]: previous }));
        const message =
          err instanceof Error
            ? err.message
            : "No fue posible actualizar el umbral de stock bajo";
        const friendly = friendlyErrorMessage(message);
        setError(friendly);
        pushToast({ message: friendly, variant: "error" });
        throw new Error(friendly);
      }
    },
    [friendlyErrorMessage, getThresholdForStore, pushToast, selectedStoreId, token],
  );

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

    const lowStock = (metrics?.low_stock_devices ?? []).filter((entry) => {
      if (!selectedStoreId) {
        return true;
      }
      return entry.store_id === selectedStoreId;
    });
    const topStores = metrics?.top_stores ?? [];

    return { totalDevices, totalItems, totalValue, lowStock, topStores };
  }, [metrics, selectedStoreId, summary]);

  const downloadInventoryReport = useCallback(
    async (reason: string) => {
      await downloadInventoryPdf(token, reason);
    },
    [token],
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
      compactMode: compactModeState,
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
      downloadInventoryReport,
      refreshOutboxStats,
      refreshSyncHistory,
      toasts,
      pushToast,
      dismissToast,
      networkAlert,
      dismissNetworkAlert,
    }),
    [
      backupHistory,
      compactModeState,
      currentLowStockThreshold,
      currentUser,
      devices,
      dismissNetworkAlert,
      dismissToast,
      downloadInventoryReport,
      enableAnalyticsAdv,
      enableCatalogPro,
      enableHybridPrep,
      enablePurchasesSales,
      enableTransfers,
      enableTwoFactor,
      error,
      formatCurrency,
      globalSearchTerm,
      handleBackup,
      handleDeviceUpdate,
      handleMovement,
      handleRetryOutbox,
      handleSync,
      lastInventoryRefresh,
      loading,
      lowStock,
      message,
      metrics,
      networkAlert,
      outbox,
      outboxError,
      outboxStats,
      pushToast,
      refreshInventoryAfterTransfer,
      refreshOutbox,
      refreshOutboxStats,
      refreshSummary,
      refreshSyncHistory,
      releaseHistory,
      selectedStore,
      selectedStoreId,
      setError,
      setGlobalSearchTerm,
      setMessage,
      setSelectedStoreId,
      setCompactMode,
      stores,
      summary,
      syncHistory,
      syncHistoryError,
      syncStatus,
      toasts,
      token,
      topStores,
      totalDevices,
      totalItems,
      totalValue,
      updateLowStockThreshold,
      updateStatus,
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

