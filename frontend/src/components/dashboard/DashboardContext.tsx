import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  downloadInventoryPdf,
  fetchBackupHistory,
  getDevices,
  getInventoryMetrics,
  getReleaseHistory,
  getStores,
  getSummary,
  getUpdateStatus,
  listSyncOutbox,
  registerMovement,
  retrySyncOutbox,
  triggerSync,
  runBackup,
} from "../../api";
import type {
  BackupJob,
  Device,
  InventoryMetrics,
  MovementInput,
  ReleaseInfo,
  Store,
  Summary,
  SyncOutboxEntry,
  UpdateStatus,
} from "../../api";

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
  formatCurrency: (value: number) => string;
  totalDevices: number;
  totalItems: number;
  totalValue: number;
  lowStockDevices: InventoryMetrics["low_stock_devices"];
  topStores: InventoryMetrics["top_stores"];
  handleMovement: (payload: MovementInput) => Promise<void>;
  refreshInventoryAfterTransfer: () => Promise<void>;
  refreshSummary: () => Promise<void>;
  handleSync: () => Promise<void>;
  handleBackup: () => Promise<void>;
  refreshOutbox: () => Promise<void>;
  handleRetryOutbox: () => Promise<void>;
  downloadInventoryReport: () => Promise<void>;
};

const DashboardContext = createContext<DashboardContextValue | undefined>(undefined);

type ProviderProps = {
  token: string;
  children: ReactNode;
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
  const [backupHistory, setBackupHistory] = useState<BackupJob[]>([]);
  const [releaseHistory, setReleaseHistory] = useState<ReleaseInfo[]>([]);
  const [updateStatus, setUpdateStatus] = useState<UpdateStatus | null>(null);
  const [selectedStoreId, setSelectedStoreId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<string | null>(null);
  const [outbox, setOutbox] = useState<SyncOutboxEntry[]>([]);
  const [outboxError, setOutboxError] = useState<string | null>(null);

  const currencyFormatter = useMemo(
    () => new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }),
    []
  );

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
        if (storesData.length > 0) {
          const firstStoreId = storesData[0].id;
          setSelectedStoreId(firstStoreId);
          const devicesData = await getDevices(token, firstStoreId);
          setDevices(devicesData);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible cargar los datos iniciales");
      } finally {
        setLoading(false);
      }
    };

    fetchInitial();
  }, [token]);

  useEffect(() => {
    const loadDevices = async () => {
      if (!selectedStoreId) {
        setDevices([]);
        return;
      }
      try {
        const devicesData = await getDevices(token, selectedStoreId);
        setDevices(devicesData);
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
        return;
      }
      try {
        const entries = await listSyncOutbox(token);
        setOutbox(entries);
        setOutboxError(null);
      } catch (err) {
        setOutboxError(err instanceof Error ? err.message : "No fue posible consultar la cola de sincronización");
      }
    };

    loadOutbox();
  }, [enableHybridPrep, token]);

  const refreshSummary = async () => {
    const [summaryData, metricsData] = await Promise.all([
      getSummary(token),
      getInventoryMetrics(token),
    ]);
    setSummary(summaryData);
    setMetrics(metricsData);
  };

  const handleMovement = async (payload: MovementInput) => {
    if (!selectedStoreId) {
      return;
    }
    try {
      setError(null);
      await registerMovement(token, selectedStoreId, payload);
      setMessage("Movimiento registrado correctamente");
      await Promise.all([
        refreshSummary(),
        getDevices(token, selectedStoreId).then(setDevices),
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo registrar el movimiento");
    }
  };

  const refreshInventoryAfterTransfer = async () => {
    await refreshSummary();
    if (selectedStoreId) {
      const devicesData = await getDevices(token, selectedStoreId);
      setDevices(devicesData);
    }
  };

  const handleSync = async () => {
    try {
      setSyncStatus("Sincronizando…");
      await triggerSync(token, selectedStoreId ?? undefined);
      setSyncStatus("Sincronización completada");
    } catch (err) {
      setSyncStatus(err instanceof Error ? err.message : "Error durante la sincronización");
    }
  };

  const handleBackup = async () => {
    try {
      setError(null);
      const job = await runBackup(token, "Respaldo manual desde tienda");
      setBackupHistory((current) => [job, ...current].slice(0, 10));
      setMessage("Respaldo generado y almacenado en el servidor central");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo generar el respaldo");
    }
  };

  const refreshOutbox = async () => {
    if (!enableHybridPrep) {
      return;
    }
    try {
      const entries = await listSyncOutbox(token);
      setOutbox(entries);
      setOutboxError(null);
    } catch (err) {
      setOutboxError(err instanceof Error ? err.message : "No se pudo actualizar la cola local");
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
    } catch (err) {
      setOutboxError(err instanceof Error ? err.message : "No se pudo reagendar la cola local");
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

