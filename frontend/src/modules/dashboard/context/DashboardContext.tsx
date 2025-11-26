import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { featureFlags } from "@/config/featureFlags";
import { syncClient } from "../../sync/services/syncClient"; // [PACK35-frontend]
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
  updateSyncOutboxPriority,
  triggerSync,
  runBackup,
  getSyncOutboxStats,
  getSyncQueueSummary,
  getSyncHybridProgress,
  getSyncHybridForecast,
  getSyncHybridBreakdown,
  getSyncHybridOverview,
  getObservabilitySnapshot,
  downloadSyncHistoryCsv,
  updateDevice,
  resolveSyncOutboxConflicts,
} from "../../../api";
import { safeArray } from "../../../utils/safeValues"; // [PACK36-dashboard-guards]
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
  SyncQueueSummary,
  SyncHybridProgress,
  SyncHybridForecast,
  SyncHybridModuleBreakdownItem,
  SyncHybridOverview,
  SyncStoreHistory,
  UpdateStatus,
  ObservabilitySnapshot,
} from "../../../api";

type DashboardContextValue = {
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
  syncHybridProgress: SyncHybridProgress | null; // [PACK35-frontend]
  syncHybridForecast: SyncHybridForecast | null; // [PACK35-frontend]
  syncHybridBreakdown: SyncHybridModuleBreakdownItem[]; // [PACK35-frontend]
  syncHybridOverview: SyncHybridOverview | null; // [PACK35-frontend]
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
  updateLowStockThreshold: (storeId: number, threshold: number) => Promise<void>;
  handleMovement: (payload: MovementInput) => Promise<void>;
  handleDeviceUpdate: (deviceId: number, updates: DeviceUpdateInput, reason: string) => Promise<void>;
  refreshInventoryAfterTransfer: () => Promise<void>;
  refreshSummary: () => Promise<void>;
  lastInventoryRefresh: Date | null;
  handleSync: () => Promise<void>;
  handleBackup: (reason: string, note?: string) => Promise<void>;
  refreshOutbox: () => Promise<void>;
  handleRetryOutbox: () => Promise<void>;
  reprioritizeOutbox: (entryId: number, priority: SyncOutboxStatsEntry["priority"], reason: string) => Promise<void>;
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

type ToastVariant = "success" | "error" | "info" | "warning";

export type ToastMessage = {
  id: number;
  message: string;
  variant: ToastVariant;
};

const DEFAULT_LOW_STOCK_THRESHOLD = 5;

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
  const [syncQueueSummary, setSyncQueueSummary] = useState<SyncQueueSummary | null>(null);
  const [syncHybridProgress, setSyncHybridProgress] =
    useState<SyncHybridProgress | null>(null); // [PACK35-frontend]
  const [syncHybridForecast, setSyncHybridForecast] =
    useState<SyncHybridForecast | null>(null); // [PACK35-frontend]
  const [syncHybridBreakdown, setSyncHybridBreakdown] =
    useState<SyncHybridModuleBreakdownItem[]>([]); // [PACK35-frontend]
  const [syncHybridOverview, setSyncHybridOverview] =
    useState<SyncHybridOverview | null>(null); // [PACK35-frontend]
  const [observability, setObservability] = useState<ObservabilitySnapshot | null>(null);
  const [observabilityError, setObservabilityError] = useState<string | null>(null);
  const [observabilityLoading, setObservabilityLoading] = useState(false);
  const [syncHistory, setSyncHistory] = useState<SyncStoreHistory[]>([]);
  const [syncHistoryError, setSyncHistoryError] = useState<string | null>(null);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [networkAlert, setNetworkAlert] = useState<string | null>(null);
  const [lowStockThresholds, setLowStockThresholds] = useState<Record<number, number>>({});

  const currencyFormatter = useMemo(
    () => new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" }),
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
        const [storesRaw, summaryRaw, metricsData, backupRaw, statusData, releasesRaw] = await Promise.all([
          getStores(token),
          getSummary(token),
          getInventoryMetrics(token),
          fetchBackupHistory(token),
          getUpdateStatus(token),
          getReleaseHistory(token),
        ]);
        // [PACK36-guards]
        const storesData = safeArray(storesRaw);
        const summaryData = safeArray(summaryRaw);
        const backupData = safeArray(backupRaw);
        const releasesData = safeArray(releasesRaw);
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
          setSyncHistory(safeArray(historyData));
          setSyncHistoryError(null);
        } catch (historyErr) {
          setSyncHistory([]);
          setSyncHistoryError(
            historyErr instanceof Error
              ? historyErr.message
              : "No fue posible consultar el historial de sincronización",
          );
        }
        const firstStore = storesData[0];
        if (firstStore) {
          setSelectedStoreId(firstStore.id);
          const devicesData = await getDevices(token, firstStore.id);
          setDevices(safeArray(devicesData));
          setLastInventoryRefresh(new Date());
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : "No fue posible cargar los datos iniciales";
        const friendly = friendlyErrorMessage(message);
        setError(friendly);
        pushToast({ message: friendly, variant: "error" }); // [PACK36-guards]
      } finally {
        setLoading(false);
      }
    };

    fetchInitial();
  }, [friendlyErrorMessage, token, pushToast]);

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
        const friendly = friendlyErrorMessage(message);
        setError(friendly);
        pushToast({ message: friendly, variant: "error" }); // [PACK36-guards]
      }
    };

    void synchronizeMetrics();
  }, [currentLowStockThreshold, friendlyErrorMessage, pushToast, stores.length, token]);

  useEffect(() => {
    const loadDevices = async () => {
      if (!selectedStoreId) {
        setDevices([]);
        return;
      }
      try {
        const devicesData = await getDevices(token, selectedStoreId);
        setDevices(safeArray(devicesData));
        setLastInventoryRefresh(new Date());
      } catch (err) {
        const message = err instanceof Error ? err.message : "No fue posible cargar los dispositivos";
        const friendly = friendlyErrorMessage(message);
        setError(friendly);
        pushToast({ message: friendly, variant: "error" }); // [PACK36-guards]
      }
    };

    loadDevices();
  }, [friendlyErrorMessage, pushToast, selectedStoreId, token]);

  const refreshObservability = useCallback(async () => {
    setObservabilityLoading(true);
    try {
      const snapshot = await getObservabilitySnapshot(token);
      setObservability(snapshot);
      setObservabilityError(null);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo consultar el estado de observabilidad";
      setObservabilityError(friendlyErrorMessage(message));
    } finally {
      setObservabilityLoading(false);
    }
  }, [friendlyErrorMessage, token]);

  useEffect(() => {
    void refreshObservability();
  }, [refreshObservability]);

  useEffect(() => {
    const loadOutbox = async () => {
      if (!enableHybridPrep) {
        setOutbox([]);
        setOutboxStats([]);
        setSyncQueueSummary(null);
        setSyncHybridProgress(null); // [PACK35-frontend]
        setSyncHybridForecast(null); // [PACK35-frontend]
        setSyncHybridBreakdown([]); // [PACK35-frontend]
        setSyncHybridOverview(null); // [PACK35-frontend]
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
        setSyncHybridProgress(overviewData.progress);
        setSyncHybridForecast(overviewData.forecast);
        setSyncHybridBreakdown(overviewData.breakdown);
        return;
      } catch (primaryError) {
        console.warn("Fallback a API híbrida previa por error en overview", primaryError);
      }
      try {
        const [entries, statsData, summaryData, hybridData] = await Promise.all([
          listSyncOutbox(token),
          getSyncOutboxStats(token),
          getSyncQueueSummary(token),
          getSyncHybridProgress(token),
        ]);
        setOutbox(entries);
        setOutboxStats(statsData);
        setSyncQueueSummary(summaryData);
        setSyncHybridProgress(hybridData);
        setOutbox(safeArray(entries)); // [PACK36-guards]
        setOutboxStats(safeArray(statsData)); // [PACK36-guards]
        setOutboxError(null);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "No fue posible consultar la cola de sincronización";
        setOutboxError(friendlyErrorMessage(message));
        setSyncHybridProgress(null);
        setSyncHybridForecast(null);
        setSyncHybridBreakdown([]);
        setSyncHybridOverview(null);
      }
    };

    loadOutbox();
  }, [enableHybridPrep, friendlyErrorMessage, token]);

  const refreshSummary = useCallback(async () => {
    const threshold = getThresholdForStore(selectedStoreId);
    const [summaryRaw, metricsData] = await Promise.all([
      getSummary(token),
      getInventoryMetrics(token, threshold),
    ]);
    setSummary(safeArray(summaryRaw)); // [PACK36-guards]
    setMetrics(metricsData);
  }, [getThresholdForStore, selectedStoreId, token]);
  const refreshStores = useCallback(async () => {
    try {
      const storesRaw = await getStores(token);
      setStores(safeArray(storesRaw));
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible actualizar las sucursales";
      const friendly = friendlyErrorMessage(message);
      setError(friendly);
      pushToast({ message: friendly, variant: "error" });
    }
  }, [friendlyErrorMessage, pushToast, token]);

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
        if (selectedStoreId) {
          const refreshedDevices = await getDevices(token, selectedStoreId);
          if (!disposed) {
            setDevices(safeArray(refreshedDevices)); // [PACK36-guards]
            setLastInventoryRefresh(new Date());
          }
        }
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "No fue posible actualizar el inventario en tiempo real";
        const friendly = friendlyErrorMessage(message);
        if (!disposed) {
          setError(friendly);
          pushToast({ message: friendly, variant: "error" }); // [PACK36-guards]
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
  }, [friendlyErrorMessage, pushToast, refreshSummary, selectedStoreId, token]);

  useEffect(() => {
    syncClient.init(); // [PACK35-frontend]
    syncClient.setToken(token);
    return () => {
      if (!token) {
        syncClient.setToken(null);
      }
    };
  }, [token]);

  const handleMovement = useCallback(
    async (payload: MovementInput) => {
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
          getDevices(token, selectedStoreId).then((items) => setDevices(safeArray(items))), // [PACK36-guards]
        ]);
        setLastInventoryRefresh(new Date());
      } catch (err) {
        const message = err instanceof Error ? err.message : "No se pudo registrar el movimiento";
        const friendly = friendlyErrorMessage(message);
        setError(friendly);
        pushToast({ message: friendly, variant: "error" });
        if (typeof navigator === "undefined" || !navigator.onLine) {
          try {
            await syncClient.enqueue({
              eventType: "inventory.movement", // [PACK35-frontend]
              payload: {
                store_id: selectedStoreId,
                movement: payload,
              },
              idempotencyKey: `inventory-movement-${selectedStoreId}-${Date.now()}`,
            });
            pushToast({ message: "Movimiento guardado en cola local.", variant: "info" });
          } catch (syncError) {
            console.warn("No fue posible guardar el movimiento en la cola local", syncError);
          }
        }
      }
    },
    [friendlyErrorMessage, pushToast, refreshSummary, selectedStoreId, token],
  );

  const handleDeviceUpdate = useCallback(
    async (
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
          getDevices(token, selectedStoreId).then((items) => setDevices(safeArray(items))), // [PACK36-guards]
        ]);
        setLastInventoryRefresh(new Date());
      } catch (err) {
        const message = err instanceof Error ? err.message : "No se pudo actualizar el dispositivo";
        const friendly = friendlyErrorMessage(message);
        setError(friendly);
        pushToast({ message: friendly, variant: "error" });
        throw new Error(friendly);
      }
    },
    [friendlyErrorMessage, pushToast, refreshSummary, selectedStoreId, token],
  );

  const refreshInventoryAfterTransfer = useCallback(async () => {
    await refreshSummary();
    if (selectedStoreId) {
      const devicesData = await getDevices(token, selectedStoreId);
      setDevices(safeArray(devicesData)); // [PACK36-guards]
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

  const handleBackup = useCallback(
    async (reason: string, note?: string) => {
      const normalizedReason = reason.trim();
      if (normalizedReason.length < 5) {
        const message = "Indica un motivo corporativo de al menos 5 caracteres.";
        setError(message);
        pushToast({ message, variant: "error" });
        return;
      }

      const resolvedNote = (note ?? "Respaldo manual desde tienda").trim() || "Respaldo manual desde tienda";

      try {
        setError(null);
        const job = await runBackup(token, normalizedReason, resolvedNote);
        setBackupHistory((current) => [job, ...current].slice(0, 10));
        setMessage("Respaldo generado y almacenado en el servidor central");
        pushToast({ message: "Respaldo generado", variant: "success" });
      } catch (err) {
        const message = err instanceof Error ? err.message : "No se pudo generar el respaldo";
        const friendly = friendlyErrorMessage(message);
        setError(friendly);
        pushToast({ message: friendly, variant: "error" });
      }
    },
    [friendlyErrorMessage, pushToast, setError, token],
  );

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
      // Si la API avanzada falla, se recurre a las solicitudes individuales.
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
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo consultar el progreso de la cola híbrida";
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
      // Si falla la vista combinada se consulta cada recurso por separado.
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
      const message =
        err instanceof Error
          ? err.message
          : "No se pudo consultar las estadísticas de la cola";
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
      // Se recurre al flujo degradado cuando la API avanzada no está disponible.
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
      const message =
        err instanceof Error ? err.message : "No se pudo consultar la cola de sincronización";
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
    [enableHybridPrep, friendlyErrorMessage, pushToast, refreshOutboxStats, token],
  );

  const exportSyncHistory = useCallback(
    async (reason: string) => {
      if (!reason || reason.trim().length < 5) {
        pushToast({ message: "Indica un motivo corporativo para la exportación.", variant: "warning" });
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
    [pushToast, token],
  );
  const conflictEntries = useMemo(
    () => outbox.filter((entry) => entry.conflict_flag),
    [outbox],
  );

  const lastOutboxConflict = useMemo(() => {
    if (conflictEntries.length === 0) {
      return null;
    }
    const timestamps = conflictEntries
      .map((entry) => new Date(entry.updated_at))
      .filter((date) => !Number.isNaN(date.getTime()));
    if (timestamps.length === 0) {
      return null;
    }
    return timestamps.sort((a, b) => b.getTime() - a.getTime())[0];
  }, [conflictEntries]);

  const handleResolveOutboxConflicts = useCallback(async () => {
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
      const message =
        err instanceof Error ? err.message : "No se pudo resolver la cola con conflictos";
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
      enablePriceLists,
      enableVariants,
      enableBundles,
      enableDte,
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
      enableBundles,
      enableVariants,
      enablePriceLists,
      enablePurchasesSales,
      enableTransfers,
      enableTwoFactor,
      enableDte,
      observability,
      observabilityError,
      observabilityLoading,
      error,
      formatCurrency,
      globalSearchTerm,
      handleBackup,
      handleDeviceUpdate,
      handleMovement,
      handleRetryOutbox,
      reprioritizeOutbox,
      handleResolveOutboxConflicts,
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
      conflictEntries,
      lastOutboxConflict,
      toggleCompactMode,
      syncHybridForecast,
      syncHybridBreakdown,
      syncHybridProgress,
      syncHybridOverview,
      refreshSyncQueueSummary,
      syncQueueSummary,
      pushToast,
      refreshInventoryAfterTransfer,
      refreshOutbox,
      exportSyncHistory,
      refreshOutboxStats,
      refreshSummary,
      refreshSyncHistory,
      refreshObservability,
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

