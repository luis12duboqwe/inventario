import { Suspense, lazy, memo, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { motion } from "framer-motion";
import { useLocation } from "react-router-dom";
import {
  AlertTriangle,
  BarChart3,
  Boxes,
  Building2,
  ClipboardCheck,
  Cog,
  DollarSign,
  FileSpreadsheet,
  RefreshCcw,
  Search,
  ShieldCheck,
  Smartphone,
  type LucideIcon,
} from "lucide-react";

const AdvancedSearch = lazy(() => import("../components/AdvancedSearch"));
const DeviceEditDialog = lazy(() => import("../components/DeviceEditDialog"));
const InventoryCategoryChart = lazy(() => import("../components/InventoryCategoryChart"));
const InventoryReportsPanel = lazy(() => import("../components/InventoryReportsPanel"));
const InventoryTable = lazy(() => import("../components/InventoryTable"));
const MovementForm = lazy(() => import("../components/MovementForm"));
import ModuleHeader, { type ModuleStatus } from "../../../shared/components/ModuleHeader";
import LoadingOverlay from "../../../shared/components/LoadingOverlay";
import Button from "../../../shared/components/ui/Button";
import TextField from "../../../shared/components/ui/TextField";
import Tabs, { type TabOption } from "../../../shared/components/ui/Tabs/Tabs";
import type {
  Device,
  DeviceImportSummary,
  DeviceListFilters,
  DeviceUpdateInput,
} from "../../../api";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import { useInventoryModule } from "../hooks/useInventoryModule";
import { promptCorporateReason } from "../../../utils/corporateReason";
import { useSmartImportManager } from "./hooks/useSmartImportManager";

type StatusBadge = {
  tone: "warning" | "success";
  text: string;
};

type StatusCard = {
  id: string;
  icon: LucideIcon;
  title: string;
  value: string;
  caption: string;
  badge?: StatusBadge;
};

type InventoryTabId =
  | "overview"
  | "movements"
  | "alerts"
  | "reports"
  | "advanced"
  | "corrections";

type TabContent = TabOption<InventoryTabId> & { content: ReactNode };

const estadoOptions: Device["estado_comercial"][] = ["nuevo", "A", "B", "C"];
const MAX_CATEGORY_SEGMENTS = 6;

const CardFallback = memo(function CardFallback({
  label,
  className,
}: {
  label: string;
  className?: string;
}) {
  const cardClassName = ["card", className].filter(Boolean).join(" ");
  return (
    <section className={cardClassName}>
      <div className="loading-overlay compact" role="status" aria-live="polite">
        <span className="spinner" aria-hidden="true" />
        <span>Cargando {label}…</span>
      </div>
    </section>
  );
});

const InlineFallback = memo(function InlineFallback({ label }: { label: string }) {
  return (
    <div className="loading-overlay compact" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>Cargando {label}…</span>
    </div>
  );
});

const resolveLowStockSeverity = (quantity: number): "critical" | "warning" | "notice" => {
  if (quantity <= 1) {
    return "critical";
  }
  if (quantity <= 3) {
    return "warning";
  }
  return "notice";
};

function InventoryPage() {
  const location = useLocation();
  const { globalSearchTerm, setGlobalSearchTerm, pushToast, setError } = useDashboard();
  const {
    token,
    enableCatalogPro,
    stores,
    selectedStoreId,
    setSelectedStoreId,
    selectedStore,
    devices,
    loading,
    totalDevices,
    totalItems,
    totalValue,
    formatCurrency,
    topStores,
    lowStockDevices,
    stockByCategory,
    handleMovement,
    handleDeviceUpdate,
    backupHistory,
    updateStatus,
    lastInventoryRefresh,
    downloadInventoryReport,
    downloadInventoryCsv,
    exportCatalogCsv,
    importCatalogCsv,
    supplierBatchOverview,
    supplierBatchLoading,
    refreshSupplierBatchOverview,
    recentMovements,
    recentMovementsLoading,
    refreshRecentMovements,
    lowStockThreshold,
    updateLowStockThreshold,
    refreshSummary,
    storeValuationSnapshot,
    fetchInventoryCurrentReport,
    downloadInventoryCurrentCsv,
    downloadInventoryCurrentPdf,
    downloadInventoryCurrentXlsx,
    fetchInventoryValueReport,
    fetchInventoryMovementsReport,
    fetchTopProductsReport,
    downloadInventoryValueCsv,
    downloadInventoryValuePdf,
    downloadInventoryValueXlsx,
    downloadInventoryMovementsCsv,
    downloadInventoryMovementsPdf,
    downloadInventoryMovementsXlsx,
    downloadTopProductsCsv,
    downloadTopProductsPdf,
    downloadTopProductsXlsx,
    smartImportInventory,
    fetchSmartImportHistory,
    fetchIncompleteDevices,
  } = useInventoryModule();

  const [inventoryQuery, setInventoryQuery] = useState("");
  const [estadoFilter, setEstadoFilter] = useState<Device["estado_comercial"] | "TODOS">("TODOS");
  const [activeTab, setActiveTab] = useState<InventoryTabId>("overview");
  const [editingDevice, setEditingDevice] = useState<Device | null>(null);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [thresholdDraft, setThresholdDraft] = useState(lowStockThreshold);
  const [isSavingThreshold, setIsSavingThreshold] = useState(false);
  const [exportingCatalog, setExportingCatalog] = useState(false);
  const [importingCatalog, setImportingCatalog] = useState(false);
  const [catalogFile, setCatalogFile] = useState<File | null>(null);
  const [lastImportSummary, setLastImportSummary] = useState<DeviceImportSummary | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const {
    smartImportFile,
    setSmartImportFile,
    smartImportPreviewState,
    smartImportResult,
    smartImportOverrides,
    smartImportHeaders,
    smartImportLoading,
    smartImportHistory,
    smartImportHistoryLoading,
    refreshSmartImportHistory,
    pendingDevices,
    pendingDevicesLoading,
    refreshPendingDevices,
    smartPreviewDirty,
    setSmartPreviewDirty,
    smartFileInputRef,
    handleSmartOverrideChange,
    handleSmartPreview,
    handleSmartCommit,
    resetSmartImportContext,
  } = useSmartImportManager({
    smartImportInventory,
    fetchSmartImportHistory,
    fetchIncompleteDevices,
    refreshSummary,
    selectedStore,
    selectedStoreId,
    pushToast,
    setError,
  });

  useEffect(() => {
    setInventoryQuery("");
    setEstadoFilter("TODOS");
    if (location.pathname.startsWith("/dashboard/inventory")) {
      setGlobalSearchTerm("");
    }
  }, [location.pathname, selectedStoreId, setGlobalSearchTerm]);

  useEffect(() => {
    if (location.pathname.startsWith("/dashboard/inventory")) {
      setInventoryQuery(globalSearchTerm);
    }
  }, [globalSearchTerm, location.pathname]);

  useEffect(() => {
    setThresholdDraft(lowStockThreshold);
  }, [lowStockThreshold]);

  const lastBackup = backupHistory.at(0) ?? null;
  const lastRefreshDisplay = lastInventoryRefresh
    ? lastInventoryRefresh.toLocaleString("es-MX")
    : "En espera de la primera actualización";

  const filteredDevices = useMemo(() => {
    const normalizedQuery = inventoryQuery.trim().toLowerCase();
    return devices.filter((device) => {
      if (estadoFilter !== "TODOS" && device.estado_comercial !== estadoFilter) {
        return false;
      }
      if (!normalizedQuery) {
        return true;
      }
      const haystack: Array<string | null | undefined> = [
        device.sku,
        device.name,
        device.imei,
        device.serial,
        device.modelo,
        device.marca,
        device.color,
        device.estado_comercial,
        device.categoria,
        device.condicion,
        device.estado,
        device.ubicacion,
        device.descripcion,
        device.proveedor,
        device.capacidad,
      ];
      return haystack.some((value) => {
        if (!value) {
          return false;
        }
        return value.toLowerCase().includes(normalizedQuery);
      });
    });
  }, [devices, estadoFilter, inventoryQuery]);

  const storeNameById = useMemo(() => {
    const mapping = new Map<number, string>();
    stores.forEach((store) => mapping.set(store.id, store.name));
    return mapping;
  }, [stores]);

  const buildSmartSummaryPdf = useCallback((summary: string) => {
    const sanitizedLines = summary
      .split("\n")
      .map((line) => line.replace(/([()\\])/g, "\\$1"));
    const streamLines = ["BT", "/F1 12 Tf", "50 800 Td"];
    sanitizedLines.forEach((line, index) => {
      if (index === 0) {
        streamLines.push(`(${line}) Tj`);
      } else {
        streamLines.push("T*");
        streamLines.push(`(${line}) Tj`);
      }
    });
    streamLines.push("ET");
    const streamContent = streamLines.join("\n");
    const objects = [
      "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
      "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
      "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
      "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
      `5 0 obj << /Length ${streamContent.length} >>\nstream\n${streamContent}\nendstream\nendobj\n`,
    ];
    const header = "%PDF-1.4\n";
    let offset = header.length;
    const xrefEntries = ["0000000000 65535 f \n"];
    const bodyParts: string[] = [];
    objects.forEach((obj) => {
      xrefEntries.push(`${String(offset).padStart(10, "0")} 00000 n \n`);
      bodyParts.push(obj);
      offset += obj.length;
    });
    const xrefPosition = offset;
    const xref = `xref\n0 ${objects.length + 1}\n${xrefEntries.join("")}`;
    const trailer = `trailer << /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefPosition}\n%%EOF`;
    return new Blob([header, ...bodyParts, xref, trailer], { type: "application/pdf" });
  }, []);

  const downloadSmartResultCsv = useCallback(() => {
    if (!smartImportResult) {
      return;
    }
    const lines = [
      "Campo,Valor",
      `Total procesados,${smartImportResult.total_procesados}`,
      `Nuevos,${smartImportResult.nuevos}`,
      `Actualizados,${smartImportResult.actualizados}`,
      `Registros incompletos,${smartImportResult.registros_incompletos}`,
      `Tiendas nuevas,${smartImportResult.tiendas_nuevas.join(" | ") || "Ninguna"}`,
    ];
    if (smartImportResult.columnas_faltantes.length > 0) {
      lines.push(
        `Columnas faltantes,"${smartImportResult.columnas_faltantes.join(" | ").replace(/"/g, '""')}"`,
      );
    } else {
      lines.push("Columnas faltantes,N/A");
    }
    if (smartImportResult.advertencias.length > 0) {
      smartImportResult.advertencias.forEach((warning, index) => {
        lines.push(
          `Advertencia ${index + 1},"${warning.replace(/"/g, '""')}"`,
        );
      });
    } else {
      lines.push("Advertencias,Ninguna");
    }
    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "importacion_inteligente_resumen.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [smartImportResult]);

  const downloadSmartResultPdf = useCallback(() => {
    if (!smartImportResult) {
      return;
    }
    const blob = buildSmartSummaryPdf(smartImportResult.resumen);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "importacion_inteligente_resumen.pdf";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [buildSmartSummaryPdf, smartImportResult]);

  const deviceFilters = useMemo<DeviceListFilters>(() => {
    const filters: DeviceListFilters = {};
    const normalizedQuery = inventoryQuery.trim();
    if (normalizedQuery) {
      filters.search = normalizedQuery;
    }
    if (estadoFilter !== "TODOS") {
      filters.estado = estadoFilter;
    }
    return filters;
  }, [inventoryQuery, estadoFilter]);

  const highlightedDevices = useMemo(
    () => new Set(lowStockDevices.map((entry) => entry.device_id)),
    [lowStockDevices],
  );

  const categoryChartData = useMemo(
    () =>
      stockByCategory.slice(0, MAX_CATEGORY_SEGMENTS).map((entry) => ({
        label: entry.label || "Sin categoría",
        value: entry.value,
      })),
    [stockByCategory],
  );

  const totalCategoryUnits = useMemo(
    () => categoryChartData.reduce((total, entry) => total + entry.value, 0),
    [categoryChartData],
  );

  const closeEditDialog = useCallback(() => {
    setIsEditDialogOpen(false);
    setEditingDevice(null);
  }, []);

  const requestSnapshotDownload = useCallback(
    async (downloader: (reason: string) => Promise<void>, successMessage: string) => {
      const defaultReason = selectedStore
        ? `Descarga inventario ${selectedStore.name}`
        : "Descarga inventario corporativo";
      const reason = promptCorporateReason(defaultReason);
      if (reason === null) {
        pushToast({ message: "Acción cancelada: se requiere motivo corporativo.", variant: "info" });
        return;
      }
      if (reason.length < 5) {
        const message = "El motivo corporativo debe tener al menos 5 caracteres.";
        setError(message);
        pushToast({ message, variant: "error" });
        return;
      }
      try {
        await downloader(reason);
        pushToast({ message: successMessage, variant: "success" });
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "No fue posible descargar el reporte de inventario.";
        setError(message);
        pushToast({ message, variant: "error" });
      }
    },
    [pushToast, selectedStore, setError],
  );

  const handleDownloadReportClick = useCallback(async () => {
    await requestSnapshotDownload(downloadInventoryReport, "PDF de inventario descargado");
  }, [downloadInventoryReport, requestSnapshotDownload]);

  const handleDownloadCsvClick = useCallback(async () => {
    await requestSnapshotDownload(downloadInventoryCsv, "CSV de inventario descargado");
  }, [downloadInventoryCsv, requestSnapshotDownload]);

  const handleExportCatalogClick = useCallback(async () => {
    if (!selectedStoreId) {
      const message = "Selecciona una sucursal para exportar el catálogo.";
      setError(message);
      pushToast({ message, variant: "error" });
      return;
    }
    setExportingCatalog(true);
    try {
      await requestSnapshotDownload(
        (reason) => exportCatalogCsv(deviceFilters, reason),
        "Catálogo CSV exportado",
      );
    } finally {
      setExportingCatalog(false);
    }
  }, [deviceFilters, exportCatalogCsv, pushToast, requestSnapshotDownload, selectedStoreId, setError]);

  const handleImportCatalogSubmit = useCallback(async () => {
    if (!catalogFile) {
      const message = "Selecciona un archivo CSV antes de importar.";
      setError(message);
      pushToast({ message, variant: "error" });
      return;
    }
    const defaultReason = selectedStore
      ? `Importar catálogo ${selectedStore.name}`
      : "Importar catálogo corporativo";
    const reason = promptCorporateReason(defaultReason);
    if (reason === null) {
      pushToast({ message: "Acción cancelada: se requiere motivo corporativo.", variant: "info" });
      return;
    }
    const normalizedReason = reason.trim();
    if (normalizedReason.length < 5) {
      const message = "Ingresa un motivo corporativo de al menos 5 caracteres.";
      setError(message);
      pushToast({ message, variant: "error" });
      return;
    }
    setImportingCatalog(true);
    try {
      const summary = await importCatalogCsv(catalogFile, normalizedReason);
      setLastImportSummary(summary);
      pushToast({
        message: `Catálogo actualizado: ${summary.created} nuevos, ${summary.updated} modificados`,
        variant: "success",
      });
      setCatalogFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible importar el catálogo corporativo.";
      setError(message);
      pushToast({ message, variant: "error" });
    } finally {
      setImportingCatalog(false);
    }
  }, [catalogFile, importCatalogCsv, pushToast, selectedStore, setError]);

  useEffect(() => {
    if (activeTab === "corrections") {
      void refreshPendingDevices();
    }
  }, [activeTab, refreshPendingDevices]);

  const updateThresholdDraftValue = useCallback((value: number) => {
    if (Number.isNaN(value)) {
      return;
    }
    const clamped = Math.max(0, Math.min(100, value));
    setThresholdDraft(clamped);
  }, []);

  const handleSaveThreshold = useCallback(async () => {
    if (!selectedStoreId) {
      const message = "Selecciona una sucursal para ajustar el umbral de alertas.";
      setError(message);
      pushToast({ message, variant: "error" });
      return;
    }
    setIsSavingThreshold(true);
    try {
      await updateLowStockThreshold(selectedStoreId, thresholdDraft);
      pushToast({ message: "Umbral de stock bajo actualizado", variant: "success" });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible guardar el nuevo umbral.";
      setError(message);
      pushToast({ message, variant: "error" });
      setThresholdDraft(lowStockThreshold);
    } finally {
      setIsSavingThreshold(false);
    }
  }, [
    pushToast,
    selectedStoreId,
    setError,
    thresholdDraft,
    updateLowStockThreshold,
    lowStockThreshold,
  ]);

  const handleSubmitDeviceUpdates = useCallback(
    async (updates: DeviceUpdateInput, reason: string) => {
      if (!editingDevice) {
        return;
      }
      try {
        await handleDeviceUpdate(editingDevice.id, updates, reason);
        closeEditDialog();
        await refreshPendingDevices();
        void refreshSummary();
      } catch (error) {
        // La notificación de error ya se gestiona desde el contexto.
      }
    },
    [closeEditDialog, editingDevice, handleDeviceUpdate, refreshPendingDevices, refreshSummary],
  );

  const resolvePendingFields = useCallback(
    (device: Device): string[] => {
      const missing: string[] = [];
      const isEmpty = (value: string | null | undefined) => !value || value.trim().length === 0;
      if (isEmpty(device.marca)) {
        missing.push("Marca");
      }
      if (isEmpty(device.modelo)) {
        missing.push("Modelo");
      }
      if (isEmpty(device.color)) {
        missing.push("Color");
      }
      if (!device.capacidad && (device.capacidad_gb == null || device.capacidad_gb === 0)) {
        missing.push("Capacidad");
      }
      if (isEmpty(device.ubicacion)) {
        missing.push("Ubicación");
      }
      if (isEmpty(device.proveedor)) {
        missing.push("Proveedor");
      }
      if (isEmpty(device.imei)) {
        missing.push("IMEI");
      }
      if (!storeNameById.get(device.store_id)) {
        missing.push("Sucursal");
      }
      return missing;
    },
    [storeNameById],
  );

  const triggerDownloadReport = useCallback(() => {
    void handleDownloadReportClick();
  }, [handleDownloadReportClick]);

  const triggerDownloadCsv = useCallback(() => {
    void handleDownloadCsvClick();
  }, [handleDownloadCsvClick]);

  const triggerRefreshSummary = useCallback(() => {
    void refreshSummary();
  }, [refreshSummary]);

  const triggerRefreshSupplierOverview = useCallback(() => {
    void refreshSupplierBatchOverview();
  }, [refreshSupplierBatchOverview]);

  const triggerRefreshRecentMovements = useCallback(() => {
    void refreshRecentMovements();
  }, [refreshRecentMovements]);

  const triggerExportCatalog = useCallback(() => {
    void handleExportCatalogClick();
  }, [handleExportCatalogClick]);

  const triggerImportCatalog = useCallback(() => {
    void handleImportCatalogSubmit();
  }, [handleImportCatalogSubmit]);

  const lowStockStats = useMemo(() => {
    let critical = 0;
    let warning = 0;
    for (const entry of lowStockDevices) {
      const severity = resolveLowStockSeverity(entry.quantity);
      if (severity === "critical") {
        critical += 1;
      } else if (severity === "warning") {
        warning += 1;
      }
    }
    return { critical, warning };
  }, [lowStockDevices]);

  let moduleStatus: ModuleStatus = "ok";
  let moduleStatusLabel = "Inventario estable";

  if (loading) {
    moduleStatus = "warning";
    moduleStatusLabel = "Actualizando inventario";
  } else if (lowStockStats.critical > 0) {
    moduleStatus = "critical";
    moduleStatusLabel = `${lowStockStats.critical} dispositivos en nivel crítico`;
  } else if (lowStockStats.warning > 0) {
    moduleStatus = "warning";
    moduleStatusLabel = `${lowStockStats.warning} dispositivos con stock bajo`;
  }

  const statusCards = useMemo<StatusCard[]>(() => {
    const refreshBadge: StatusBadge = lastInventoryRefresh
      ? { tone: "success", text: "Auto" }
      : { tone: "warning", text: "Sin datos" };

    const versionBadge: StatusBadge | undefined = updateStatus?.is_update_available
      ? { tone: "warning", text: `Actualizar a ${updateStatus.latest_version}` }
      : { tone: "success", text: "Sistema al día" };

    return [
      {
        id: "stores",
        icon: Building2,
        title: "Sucursales",
        value: `${stores.length}`,
        caption: "Configuradas",
      },
      {
        id: "devices",
        icon: Smartphone,
        title: "Dispositivos",
        value: `${totalDevices}`,
        caption: "Catalogados",
      },
      {
        id: "units",
        icon: Boxes,
        title: "Unidades",
        value: `${totalItems}`,
        caption: "En stock",
      },
      {
        id: "value",
        icon: DollarSign,
        title: "Valor total",
        value: formatCurrency(totalValue),
        caption: "Inventario consolidado",
      },
      {
        id: "backup",
        icon: ShieldCheck,
        title: "Último respaldo",
        value: lastBackup
          ? new Date(lastBackup.executed_at).toLocaleString("es-MX")
          : "Aún no se generan respaldos",
        caption: lastBackup ? lastBackup.mode : "Programado cada 12 h",
      },
      {
        id: "version",
        icon: Cog,
        title: "Versión",
        value: updateStatus?.current_version ?? "Desconocida",
        caption: updateStatus?.latest_version
          ? `Última publicada: ${updateStatus.latest_version}`
          : "Historial actualizado",
        badge: versionBadge,
      },
      {
        id: "refresh",
        icon: RefreshCcw,
        title: "Actualización en vivo",
        value: lastInventoryRefresh
          ? lastInventoryRefresh.toLocaleTimeString("es-MX")
          : "Sincronizando…",
        caption: lastRefreshDisplay,
        badge: refreshBadge,
      },
    ];
  }, [
    formatCurrency,
    lastBackup,
    lastInventoryRefresh,
    lastRefreshDisplay,
    stores,
    totalDevices,
    totalItems,
    totalValue,
    updateStatus,
  ]);

  const overviewContent: ReactNode = (
    <div className="section-grid">
      <section className="card wide">
        <header className="card-header">
          <div>
            <h2>Salud de inventario</h2>
            <p className="card-subtitle">Indicadores clave de todas las tiendas.</p>
          </div>
          {loading ? <span className="pill neutral">Cargando datos…</span> : null}
        </header>
        <div className="status-grid">
          {statusCards.map((cardInfo) => {
            const Icon = cardInfo.icon;
            return (
              <motion.article
                key={cardInfo.id}
                className="status-card"
                whileHover={{ y: -6, scale: 1.01 }}
                transition={{ type: "spring", stiffness: 260, damping: 20 }}
              >
                <span className="status-card-icon" aria-hidden>
                  <Icon size={26} strokeWidth={1.6} />
                </span>
                <div className="status-card-body">
                  <h3>{cardInfo.title}</h3>
                  <p className="status-value">{cardInfo.value}</p>
                  <span className="status-caption">{cardInfo.caption}</span>
                </div>
                {cardInfo.badge ? (
                  <span className={`badge ${cardInfo.badge.tone}`}>{cardInfo.badge.text}</span>
                ) : null}
              </motion.article>
            );
          })}
        </div>
      </section>

      <section className="card">
        <header className="card-header">
          <h2>Seleccionar sucursal</h2>
        </header>
        <select
          value={selectedStoreId ?? ""}
          onChange={(event) => setSelectedStoreId(event.target.value ? Number(event.target.value) : null)}
        >
          {stores.map((store) => (
            <option key={store.id} value={store.id}>
              {store.name}
            </option>
          ))}
        </select>
        {selectedStore ? (
          <p className="muted-text">
            {selectedStore.location ? `${selectedStore.location} · ` : ""}
            Zona horaria: {selectedStore.timezone}
          </p>
        ) : null}
      </section>

      {storeValuationSnapshot ? (
        <section className="card">
          <header className="card-header">
            <div>
              <h2>Conciliación contable</h2>
              <p className="card-subtitle">
                Valor registrado vs. calculado en {storeValuationSnapshot.storeName}.
              </p>
            </div>
            <span
              className={`pill ${
                storeValuationSnapshot.hasRelevantDifference ? "warning" : "success"
              }`}
            >
              {storeValuationSnapshot.hasRelevantDifference
                ? "Revisión requerida"
                : "Sin diferencias"}
            </span>
          </header>
          <ul className="metrics-list">
            <li>
              <strong>Valor contable registrado</strong>
              <span>{formatCurrency(storeValuationSnapshot.registeredValue)}</span>
            </li>
            <li>
              <strong>Valor operativo calculado</strong>
              <span>{formatCurrency(storeValuationSnapshot.calculatedValue)}</span>
            </li>
            <li>
              <strong>Diferencia neta</strong>
              <span>{formatCurrency(storeValuationSnapshot.difference)}</span>
            </li>
            {storeValuationSnapshot.differencePercent !== null ? (
              <li>
                <strong>Variación porcentual</strong>
                <span>{`${Math.abs(storeValuationSnapshot.differencePercent).toFixed(2)} %`}</span>
              </li>
            ) : null}
          </ul>
          <p className="muted-text">
            {storeValuationSnapshot.hasRelevantDifference
              ? `El valor calculado es ${
                  storeValuationSnapshot.difference > 0 ? "mayor" : "menor"
                } que el contable por ${formatCurrency(
                  Math.abs(storeValuationSnapshot.difference),
                )}. Revisa la bitácora corporativa antes de cerrar el periodo.`
              : "Los valores coinciden con el registro contable corporativo."}
          </p>
        </section>
      ) : null}

      <section className="card">
        <h2>Top sucursales por valor</h2>
        {topStores.length === 0 ? (
          <p className="muted-text">No hay datos suficientes para calcular el ranking.</p>
        ) : (
          <ul className="metrics-list">
            {topStores.map((storeMetric) => (
              <li key={storeMetric.store_id}>
                <strong>{storeMetric.store_name}</strong> · {storeMetric.device_count} dispositivos · {storeMetric.total_units}
                unidades ·<span> {formatCurrency(storeMetric.total_value)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card chart-card">
        <header className="card-header">
          <div>
            <h2>Stock por categoría</h2>
            <p className="card-subtitle">Visualiza la distribución de existencias en inventario.</p>
          </div>
          <span className="pill neutral">
            Total {totalCategoryUnits.toLocaleString("es-MX")}
            {" "}uds
          </span>
        </header>
        <Suspense fallback={<InlineFallback label="gráfica por categoría" />}>
          <InventoryCategoryChart data={categoryChartData} totalUnits={totalCategoryUnits} />
        </Suspense>
      </section>

      <section className="card wide">
        <header className="card-header">
          <div>
            <h2>Lotes recientes por proveedor</h2>
            <p className="card-subtitle">
              Seguimiento de compras asociadas a {selectedStore ? selectedStore.name : "cada sucursal"}.
            </p>
          </div>
          <div className="card-actions">
            <Button
              variant="ghost"
              size="sm"
              type="button"
              onClick={triggerRefreshSupplierOverview}
              disabled={supplierBatchLoading}
            >
              {supplierBatchLoading ? "Actualizando…" : "Actualizar"}
            </Button>
          </div>
        </header>
        {supplierBatchLoading ? (
          <p className="muted-text">Cargando lotes recientes…</p>
        ) : supplierBatchOverview.length === 0 ? (
          <p className="muted-text">
            {selectedStore
              ? "Aún no se registran lotes para esta sucursal."
              : "Selecciona una sucursal para consultar sus lotes recientes."}
          </p>
        ) : (
          <ul className="metrics-list">
            {supplierBatchOverview.map((item) => (
              <li key={item.supplier_id}>
                <strong>{item.supplier_name}</strong> · {item.batch_count} lote
                {item.batch_count === 1 ? "" : "s"}
                <div>
                  {item.total_quantity} unidades · {formatCurrency(item.total_value)}
                </div>
                <div className="muted-text">
                  Último lote {item.latest_batch_code ?? "N/D"} —
                  {" "}
                  {new Date(item.latest_purchase_date).toLocaleDateString("es-MX")}
                  {item.latest_unit_cost != null ? (
                    <span>
                      {" "}· Costo unitario reciente: {formatCurrency(item.latest_unit_cost)}
                    </span>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <header className="card-header">
          <div>
            <h2>Últimos movimientos</h2>
            <p className="card-subtitle">Entradas, salidas y ajustes más recientes.</p>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={triggerRefreshRecentMovements}
            disabled={recentMovementsLoading}
            leadingIcon={<RefreshCcw aria-hidden size={16} />}
          >
            {recentMovementsLoading ? "Actualizando…" : "Actualizar"}
          </Button>
        </header>
        {recentMovementsLoading ? (
          <p className="muted-text">Cargando movimientos recientes…</p>
        ) : recentMovements.length === 0 ? (
          <p className="muted-text">No se registran movimientos en los últimos 14 días.</p>
        ) : (
          <ul className="inventory-timeline">
            {recentMovements.map((movement) => {
              const destination = movement.sucursal_destino ?? "Inventario corporativo";
              const origin = movement.sucursal_origen;
              return (
                <li
                  key={movement.id}
                  className={`inventory-timeline__item inventory-timeline__item--${movement.tipo_movimiento}`}
                >
                  <div className="inventory-timeline__meta">
                    <span className="inventory-timeline__type">{movement.tipo_movimiento.toUpperCase()}</span>
                    <span className="inventory-timeline__date">
                      {new Date(movement.fecha).toLocaleString("es-MX")}
                    </span>
                  </div>
                  <div className="inventory-timeline__summary">
                    <span>
                      {movement.cantidad.toLocaleString("es-MX")} unidades · {formatCurrency(movement.valor_total)}
                    </span>
                    {movement.usuario ? (
                      <span className="inventory-timeline__user">{movement.usuario}</span>
                    ) : null}
                  </div>
                  <p className="inventory-timeline__route">
                    {origin ? `${origin} → ${destination}` : destination}
                  </p>
                  {movement.comentario ? (
                    <p className="inventory-timeline__comment">{movement.comentario}</p>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );

  const movementsContent: ReactNode = (
    <div className="section-grid">
      <section className="card wide">
        <header className="card-header">
          <div>
            <h2>Inventario actual</h2>
            <p className="card-subtitle">Consulta existencias y registra movimientos en la misma vista.</p>
          </div>
          <div className="inventory-meta">
            <span className="muted-text">
              Mostrando {filteredDevices.length} de {devices.length} dispositivos
            </span>
            <span className="inventory-last-update">Última actualización: {lastRefreshDisplay}</span>
          </div>
        </header>
        <div className="inventory-controls">
          <TextField
            className="inventory-controls__search"
            type="search"
            label="Buscar por IMEI, modelo o SKU"
            hideLabel
            value={inventoryQuery}
            onChange={(event) => {
              const value = event.target.value;
              setInventoryQuery(value);
              if (location.pathname.startsWith("/dashboard/inventory")) {
                setGlobalSearchTerm(value);
              }
            }}
            placeholder="Buscar por IMEI, modelo o SKU"
            leadingIcon={<Search size={16} aria-hidden />}
            autoComplete="off"
          />
          <label className="select-inline">
            <span>Estado comercial</span>
            <select
              value={estadoFilter}
              onChange={(event) =>
                setEstadoFilter(event.target.value as Device["estado_comercial"] | "TODOS")
              }
            >
              <option value="TODOS">Todos</option>
              {estadoOptions.map((estado) => (
                <option key={estado} value={estado}>
                  {estado === "nuevo" ? "Nuevo" : `Grado ${estado}`}
                </option>
              ))}
            </select>
          </label>
        </div>
        <Suspense fallback={<InlineFallback label="tabla de inventario" />}>
          <InventoryTable
            devices={filteredDevices}
            highlightedDeviceIds={highlightedDevices}
            emptyMessage={
              inventoryQuery.trim() || estadoFilter !== "TODOS"
                ? "No se encontraron dispositivos con los filtros actuales."
                : undefined
            }
            onEditDevice={(device) => {
              setEditingDevice(device);
              setIsEditDialogOpen(true);
            }}
          />
        </Suspense>
      </section>

      <section className="card">
        <header className="card-header">
          <div>
            <h2>Registrar movimiento</h2>
            <p className="card-subtitle">Ajustes, entradas y salidas sincronizadas con inventario.</p>
          </div>
          <div className="card-actions">
            <Button variant="primary" size="sm" type="button" onClick={triggerRefreshSummary}>
              Actualizar métricas
            </Button>
            <Button
              variant="ghost"
              size="sm"
              type="button"
              onClick={triggerDownloadReport}
              leadingIcon={<FileSpreadsheet aria-hidden size={16} />}
            >
              Descargar PDF
            </Button>
            <Button
              variant="ghost"
              size="sm"
              type="button"
              onClick={triggerDownloadCsv}
              leadingIcon={<FileSpreadsheet aria-hidden size={16} />}
            >
              Descargar CSV
            </Button>
          </div>
        </header>
        <Suspense fallback={<InlineFallback label="formulario de movimientos" />}>
          <MovementForm devices={devices} onSubmit={handleMovement} />
        </Suspense>
      </section>
    </div>
  );

  const alertsContent: ReactNode = (
    <section className="card">
      <header className="card-header">
        <div>
          <h2>Alertas de inventario bajo</h2>
          <p className="card-subtitle">Seguimiento inmediato de piezas críticas.</p>
        </div>
        <span className={`pill ${lowStockDevices.length === 0 ? "success" : "warning"}`}>
          {lowStockDevices.length === 0
            ? "Sin alertas"
            : `${lowStockDevices.length} alerta${lowStockDevices.length === 1 ? "" : "s"}`}
        </span>
      </header>
      <div className="threshold-settings">
        <label htmlFor="low-stock-threshold">
          Umbral por sucursal ({thresholdDraft} unidad{thresholdDraft === 1 ? "" : "es"})
        </label>
        <div className="threshold-inputs">
          <input
            id="low-stock-threshold"
            type="range"
            min={0}
            max={100}
            value={thresholdDraft}
            onChange={(event) => updateThresholdDraftValue(Number(event.target.value))}
            disabled={!selectedStoreId || isSavingThreshold}
          />
          <input
            type="number"
            min={0}
            max={100}
            value={thresholdDraft}
            onChange={(event) => updateThresholdDraftValue(Number(event.target.value))}
            disabled={!selectedStoreId || isSavingThreshold}
          />
          <Button
            variant="secondary"
            size="sm"
            type="button"
            onClick={() => {
              void handleSaveThreshold();
            }}
            disabled={
              !selectedStoreId || isSavingThreshold || thresholdDraft === lowStockThreshold
            }
          >
            {isSavingThreshold ? "Guardando…" : "Guardar umbral"}
          </Button>
        </div>
      </div>
      {lowStockDevices.length === 0 ? (
        <p className="muted-text">No hay alertas por ahora.</p>
      ) : (
        <ul className="low-stock-list">
          {lowStockDevices.map((device) => {
            const severity = resolveLowStockSeverity(device.quantity);
            return (
              <motion.li
                key={device.device_id}
                className={`low-stock-item ${severity}`}
                whileHover={{ x: 6 }}
                transition={{ type: "spring", stiffness: 300, damping: 24 }}
              >
                <span className="low-stock-icon">
                  <AlertTriangle size={18} />
                </span>
                <div className="low-stock-body">
                  <strong>{device.sku}</strong>
                  <span>
                    {device.name} · {device.store_name}
                  </span>
                </div>
                <div className="low-stock-meta">
                  <span className="low-stock-quantity">{device.quantity} uds</span>
                  <span>{formatCurrency(device.inventory_value)}</span>
                </div>
              </motion.li>
            );
          })}
        </ul>
      )}
    </section>
  );

  const reportsContent: ReactNode = (
    <Suspense fallback={<CardFallback label="panel de reportes" />}>
      <InventoryReportsPanel
        stores={stores}
        selectedStoreId={selectedStoreId}
        formatCurrency={formatCurrency}
        fetchInventoryCurrentReport={fetchInventoryCurrentReport}
        downloadInventoryCurrentCsv={downloadInventoryCurrentCsv}
        downloadInventoryCurrentPdf={downloadInventoryCurrentPdf}
        downloadInventoryCurrentXlsx={downloadInventoryCurrentXlsx}
        fetchInventoryValueReport={fetchInventoryValueReport}
        fetchInventoryMovementsReport={fetchInventoryMovementsReport}
        fetchTopProductsReport={fetchTopProductsReport}
        requestDownloadWithReason={requestSnapshotDownload}
        downloadInventoryValueCsv={downloadInventoryValueCsv}
        downloadInventoryValuePdf={downloadInventoryValuePdf}
        downloadInventoryValueXlsx={downloadInventoryValueXlsx}
        downloadInventoryMovementsCsv={downloadInventoryMovementsCsv}
        downloadInventoryMovementsPdf={downloadInventoryMovementsPdf}
        downloadInventoryMovementsXlsx={downloadInventoryMovementsXlsx}
        downloadTopProductsCsv={downloadTopProductsCsv}
        downloadTopProductsPdf={downloadTopProductsPdf}
        downloadTopProductsXlsx={downloadTopProductsXlsx}
      />
    </Suspense>
  );

  const advancedContent: ReactNode = enableCatalogPro ? (
    <div className="section-grid">
      <Suspense fallback={<CardFallback label="búsqueda avanzada" className="catalog-card fade-in" />}>
        <AdvancedSearch token={token} />
      </Suspense>
      <section className="card">
        <header className="card-header">
          <div>
            <h2>Herramientas de catálogo</h2>
            <p className="card-subtitle">
              Importa o exporta productos con campos extendidos y mantén el inventario alineado.
            </p>
          </div>
        </header>
        <div className="catalog-tools">
          <div className="catalog-actions">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={triggerExportCatalog}
              disabled={exportingCatalog}
            >
              {exportingCatalog ? "Exportando…" : "Exportar catálogo CSV"}
            </Button>
          </div>
          <div className="catalog-import">
            <label className="file-input">
              <span>Archivo CSV</span>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,text/csv"
                onChange={(event) => {
                  const file = event.target.files?.[0] ?? null;
                  setCatalogFile(file);
                }}
              />
              <small className="muted-text">
                {catalogFile
                  ? `Seleccionado: ${catalogFile.name}`
                  : "Incluye encabezados sku, name, categoria, condicion, estado, costo_compra, precio_venta, ubicacion, fecha_ingreso, descripcion"}
              </small>
            </label>
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={triggerImportCatalog}
              disabled={importingCatalog || !catalogFile}
            >
              {importingCatalog ? "Importando…" : "Importar catálogo"}
            </Button>
          </div>
          {lastImportSummary ? (
            <div className="catalog-summary">
              <p className="muted-text">
                Creados: {lastImportSummary.created} · Actualizados: {lastImportSummary.updated} · Omitidos: {lastImportSummary.skipped}
              </p>
              {lastImportSummary.errors.length > 0 ? (
                <ul className="error-list">
                  {lastImportSummary.errors.slice(0, 5).map((error) => (
                    <li key={`${error.row}-${error.message}`}>
                      Fila {error.row}: {error.message}
                    </li>
                  ))}
                  {lastImportSummary.errors.length > 5 ? (
                    <li className="muted-text">Se omitieron {lastImportSummary.errors.length - 5} errores adicionales.</li>
                  ) : null}
                </ul>
              ) : (
                <p className="muted-text">No se registraron errores en la última importación.</p>
              )}
            </div>
          ) : (
            <p className="muted-text">
              Descarga la plantilla actual para conservar todos los campos: SKU, categoría, condición, estado, costo_compra, precio_venta,
              ubicación, fechas y descripción.
            </p>
          )}
          <div className="smart-import">
            <div className="smart-import__header">
              <h3>Importar desde Excel (inteligente)</h3>
              <p className="muted-text">
                Analiza cualquier archivo Excel o CSV, detecta columnas clave y completa el inventario aunque falten campos.
              </p>
            </div>
            <label className="file-input">
              <span>Archivo Excel o CSV</span>
              <input
                ref={smartFileInputRef}
                type="file"
                accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,.csv,text/csv"
                onChange={(event) => {
                  const file = event.target.files?.[0] ?? null;
                  setSmartImportFile(file);
                  resetSmartImportContext();
                }}
              />
              <small className="muted-text">
                {smartImportFile
                  ? `Seleccionado: ${smartImportFile.name}`
                  : "Soporta encabezados libres como tienda, modelo, IMEI, precio, cantidad, estado o ubicación."}
              </small>
            </label>
            <div className="smart-import__actions">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => {
                  void handleSmartPreview();
                }}
                disabled={!smartImportFile || smartImportLoading}
              >
                {smartImportLoading ? "Analizando…" : "Analizar estructura"}
              </Button>
              <Button
                type="button"
                variant="primary"
                size="sm"
                onClick={() => {
                  void handleSmartCommit();
                }}
                disabled={
                  smartImportLoading ||
                  !smartImportFile ||
                  smartPreviewDirty ||
                  (!smartImportPreviewState && !smartImportResult)
                }
              >
                {smartImportLoading ? "Procesando…" : "Importar desde Excel (inteligente)"}
              </Button>
            </div>
            {smartPreviewDirty ? (
              <p className="smart-import__note smart-import__note--warning">
                Reanaliza el archivo para aplicar las reasignaciones de columnas.
              </p>
            ) : null}
            {smartImportLoading ? <InlineFallback label="importación inteligente" /> : null}
            {smartImportPreviewState ? (
              <div className="smart-import__preview">
                <h4>Columnas detectadas</h4>
                <p className="muted-text">
                  Registros incompletos estimados: {smartImportPreviewState.registros_incompletos_estimados}
                </p>
                {smartImportPreviewState.columnas_faltantes.length > 0 ? (
                  <p className="smart-import__note smart-import__note--warning">
                    Columnas faltantes: {smartImportPreviewState.columnas_faltantes.join(", ")}
                  </p>
                ) : (
                  <p className="smart-import__note smart-import__note--success">
                    Todas las columnas clave fueron identificadas.
                  </p>
                )}
                {smartImportPreviewState.advertencias.length > 0 ? (
                  <ul className="smart-import__warnings">
                    {smartImportPreviewState.advertencias.map((warning, index) => {
                      const [title, ...rest] = warning.split(":");
                      if (rest.length === 0) {
                        return <li key={`preview-warning-${index}`}>{warning}</li>;
                      }
                      const detail = rest.join(":").trim();
                      return (
                        <li key={`preview-warning-${index}`}>
                          <span className="smart-import__warning-title">{title}</span>
                          {detail ? (
                            <>
                              <span className="smart-import__warning-separator">·</span>
                              <span className="smart-import__warning-detail">«{detail}»</span>
                            </>
                          ) : null}
                        </li>
                      );
                    })}
                  </ul>
                ) : null}
                <div className="smart-import__table-wrapper">
                  <table className="smart-import__table">
                    <thead>
                      <tr>
                        <th>Campo del sistema</th>
                        <th>Estado</th>
                        <th>Encabezado detectado / reasignación</th>
                        <th>Tipo</th>
                        <th>Ejemplos</th>
                      </tr>
                    </thead>
                    <tbody>
                      {smartImportPreviewState.columnas.map((match) => {
                        const currentHeader = smartImportOverrides[match.campo] ?? match.encabezado_origen ?? "";
                        return (
                          <tr key={match.campo}>
                            <td>{match.campo}</td>
                            <td>
                              <span className={`smart-import-status smart-import-status--${match.estado}`}>
                                {match.estado === "ok" ? "Detectada" : match.estado === "pendiente" ? "Parcial" : "Faltante"}
                              </span>
                            </td>
                            <td>
                              <select
                                value={currentHeader}
                                onChange={(event) => handleSmartOverrideChange(match.campo, event.target.value)}
                              >
                                <option value="">Automático</option>
                                {smartImportHeaders.map((header) => (
                                  <option key={`${match.campo}-${header}`} value={header}>
                                    {header}
                                  </option>
                                ))}
                              </select>
                            </td>
                            <td>{match.tipo_dato ?? "—"}</td>
                            <td>
                              {match.ejemplos.length === 0 ? (
                                <span className="muted-text">Sin datos de muestra</span>
                              ) : (
                                <ul className="smart-import__samples">
                                  {match.ejemplos.map((sample) => (
                                    <li key={`${match.campo}-${sample}`}>{sample}</li>
                                  ))}
                                </ul>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <p className="muted-text">
                Analiza un archivo para obtener el mapa de columnas y detectar advertencias antes de importar.
              </p>
            )}
            {smartImportResult ? (
              <div className="smart-import__result">
                <h4>Resumen de importación</h4>
                <pre className="smart-import__summary">{smartImportResult.resumen}</pre>
                {smartImportResult.columnas_faltantes.length > 0 ? (
                  <p className="smart-import__note smart-import__note--warning">
                    Columnas sin datos definitivos: {smartImportResult.columnas_faltantes.join(", ")}
                  </p>
                ) : null}
                {smartImportResult.tiendas_nuevas.length > 0 ? (
                  <p className="smart-import__note smart-import__note--success">
                    Tiendas creadas automáticamente: {smartImportResult.tiendas_nuevas.join(", ")}
                  </p>
                ) : null}
                {typeof smartImportResult.duracion_segundos === "number" ? (
                  <p className="muted-text">
                    Tiempo estimado: {smartImportResult.duracion_segundos.toFixed(1)} segundos
                  </p>
                ) : null}
                {smartImportResult.advertencias.length > 0 ? (
                  <ul className="smart-import__warnings">
                    {smartImportResult.advertencias.map((warning, index) => {
                      const [title, ...rest] = warning.split(":");
                      if (rest.length === 0) {
                        return <li key={`resultado-${index}`}>{warning}</li>;
                      }
                      const detail = rest.join(":").trim();
                      return (
                        <li key={`resultado-${index}`}>
                          <span className="smart-import__warning-title">{title}</span>
                          {detail ? (
                            <>
                              <span className="smart-import__warning-separator">·</span>
                              <span className="smart-import__warning-detail">«{detail}»</span>
                            </>
                          ) : null}
                        </li>
                      );
                    })}
                  </ul>
                ) : null}
                <div className="smart-import__result-actions">
                  <Button variant="ghost" size="sm" type="button" onClick={downloadSmartResultCsv}>
                    Descargar resumen CSV
                  </Button>
                  <Button variant="ghost" size="sm" type="button" onClick={downloadSmartResultPdf}>
                    Descargar resumen PDF
                  </Button>
                </div>
              </div>
            ) : null}
            <div className="smart-import__history">
              <div className="smart-import__history-header">
                <h4>Historial reciente</h4>
                <Button
                  variant="ghost"
                  size="sm"
                  type="button"
                  onClick={() => void refreshSmartImportHistory()}
                  disabled={smartImportHistoryLoading}
                >
                  Actualizar
                </Button>
              </div>
              {smartImportHistoryLoading ? (
                <InlineFallback label="historial de importaciones" />
              ) : smartImportHistory.length === 0 ? (
                <p className="muted-text">Aún no se registran importaciones inteligentes.</p>
              ) : (
                <ul className="smart-import__history-list">
                  {smartImportHistory.map((entry) => (
                    <li key={entry.id}>
                      <strong>{entry.nombre_archivo}</strong>
                      <span>{new Date(entry.fecha).toLocaleString("es-MX")}</span>
                      <span>
                        Procesados: {entry.total_registros} · Nuevos: {entry.nuevos} · Actualizados: {entry.actualizados}
                      </span>
                      {typeof entry.duracion_segundos === "number" ? (
                        <span>Duración: {entry.duracion_segundos.toFixed(1)} s</span>
                      ) : null}
                      {entry.registros_incompletos > 0 ? (
                        <span className="smart-import__history-warning">
                          Incompletos: {entry.registros_incompletos}
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  ) : (
    <section className="card">
      <header className="card-header">
        <h2>Búsqueda avanzada</h2>
      </header>
      <p className="muted-text">
        Activa el flag corporativo <code>SOFTMOBILE_ENABLE_CATALOG_PRO</code> para habilitar el catálogo profesional.
      </p>
    </section>
  );

  const correctionsContent: ReactNode = (
    <div className="section-grid">
      <section className="card wide">
        <header className="card-header">
          <div>
            <h2>Correcciones pendientes</h2>
            <p className="card-subtitle">
              Completa la información faltante detectada durante las importaciones inteligentes.
            </p>
          </div>
          <div className="card-actions">
            <Button
              variant="ghost"
              size="sm"
              type="button"
              onClick={() => void refreshPendingDevices()}
              disabled={pendingDevicesLoading}
            >
              Actualizar
            </Button>
          </div>
        </header>
        {pendingDevicesLoading ? (
          <InlineFallback label="dispositivos pendientes" />
        ) : pendingDevices.length === 0 ? (
          <p className="muted-text">
            No hay dispositivos con datos pendientes. Verifica las próximas importaciones para mantenerlos al día.
          </p>
        ) : (
          <div className="pending-corrections">
            <p className="muted-text">
              Dispositivos detectados: {pendingDevices.length}. Selecciona “Completar datos” para abrir la ficha y resolver los
              campos faltantes.
            </p>
            <div className="pending-corrections__table-wrapper">
              <table className="pending-corrections__table">
                <thead>
                  <tr>
                    <th>Dispositivo</th>
                    <th>Sucursal</th>
                    <th>Campos faltantes</th>
                    <th>Estado</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {pendingDevices.map((device) => {
                    const missingFields = resolvePendingFields(device);
                    const storeName =
                      storeNameById.get(device.store_id) ?? `Sucursal nueva (ID ${device.store_id})`;
                    return (
                      <tr key={device.id}>
                        <td>
                          <div className="pending-corrections__device">
                            <strong>{device.name}</strong>
                            <span className="muted-text">SKU {device.sku}</span>
                          </div>
                        </td>
                        <td>{storeName}</td>
                        <td>
                          {missingFields.length === 0 ? (
                            <span className="muted-text">Sin pendientes</span>
                          ) : (
                            <ul className="pending-corrections__missing">
                              {missingFields.map((field) => (
                                <li key={`${device.id}-${field}`}>{field}</li>
                              ))}
                            </ul>
                          )}
                        </td>
                        <td>
                          <span
                            className={`smart-import-status smart-import-status--${
                              device.completo ? "ok" : "falta"
                            }`}
                          >
                            {device.completo ? "Completo" : "Pendiente"}
                          </span>
                        </td>
                        <td>
                          <Button
                            type="button"
                            variant="secondary"
                            size="sm"
                            onClick={() => {
                              setEditingDevice(device);
                              setIsEditDialogOpen(true);
                            }}
                          >
                            Completar datos
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </div>
  );

  const inventoryTabs = useMemo<TabContent[]>(
    () => [
      {
        id: "overview",
        label: "Vista general",
        icon: <Boxes size={16} aria-hidden />,
        content: overviewContent,
      },
      {
        id: "movements",
        label: "Movimientos",
        icon: <RefreshCcw size={16} aria-hidden />,
        content: movementsContent,
      },
      {
        id: "alerts",
        label: "Alertas",
        icon: <AlertTriangle size={16} aria-hidden />,
        content: alertsContent,
      },
      {
        id: "reports",
        label: "Reportes",
        icon: <BarChart3 size={16} aria-hidden />,
        content: reportsContent,
      },
      {
        id: "advanced",
        label: "Búsqueda avanzada",
        icon: <Search size={16} aria-hidden />,
        content: advancedContent,
      },
      {
        id: "corrections",
        label: "Correcciones pendientes",
        icon: <ClipboardCheck size={16} aria-hidden />,
        content: correctionsContent,
      },
    ],
    [
      advancedContent,
      alertsContent,
      correctionsContent,
      movementsContent,
      overviewContent,
      reportsContent,
    ],
  );

  return (
    <div className="module-content">
      <ModuleHeader
        icon={<Boxes aria-hidden="true" />}
        title="Inventario corporativo"
        subtitle="Gestión de existencias, auditoría de movimientos y respaldos en tiempo real"
        status={moduleStatus}
        statusLabel={moduleStatusLabel}
      />
      <LoadingOverlay visible={loading} label="Sincronizando inventario..." />
      <Tabs tabs={inventoryTabs} activeTab={activeTab} onTabChange={setActiveTab} />
      <Suspense fallback={null}>
        <DeviceEditDialog
          device={editingDevice}
          open={isEditDialogOpen}
          onClose={closeEditDialog}
          onSubmit={handleSubmitDeviceUpdates}
        />
      </Suspense>
    </div>
  );
}

export default InventoryPage;
