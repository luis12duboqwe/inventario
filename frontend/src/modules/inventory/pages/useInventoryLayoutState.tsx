import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  AlertTriangle,
  Boxes,
  Building2,
  Cog,
  DollarSign,
  RefreshCcw,
  ShieldCheck,
  Smartphone,
} from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import type {
  Device,
  DeviceImportSummary,
  DeviceListFilters,
  DeviceUpdateInput,
} from "../../../api";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import { useInventoryModule } from "../hooks/useInventoryModule";
import { useSmartImportManager } from "./hooks/useSmartImportManager";
import { promptCorporateReason } from "../../../utils/corporateReason";
import type { InventoryLayoutContextValue, StatusCard } from "./context/InventoryLayoutContext";

export type InventoryTabId = "productos" | "movimientos" | "proveedores" | "alertas";

const INVENTORY_TABS: Array<{
  id: InventoryTabId;
  label: string;
  icon: JSX.Element;
  path: string;
}> = [
  { id: "productos", label: "Productos", icon: <Boxes size={16} aria-hidden="true" />, path: "productos" },
  { id: "movimientos", label: "Movimientos", icon: <RefreshCcw size={16} aria-hidden="true" />, path: "movimientos" },
  { id: "proveedores", label: "Proveedores", icon: <Building2 size={16} aria-hidden="true" />, path: "proveedores" },
  { id: "alertas", label: "Alertas", icon: <AlertTriangle size={16} aria-hidden="true" />, path: "alertas" },
];

export type InventoryLayoutState = {
  contextValue: InventoryLayoutContextValue;
  tabOptions: Array<{ id: InventoryTabId; label: string; icon: JSX.Element }>;
  activeTab: InventoryTabId;
  handleTabChange: (tabId: InventoryTabId) => void;
  moduleStatus: "ok" | "warning" | "critical";
  moduleStatusLabel: string;
  loading: boolean;
  editingDevice: Device | null;
  isEditDialogOpen: boolean;
  closeEditDialog: () => void;
  handleSubmitDeviceUpdates: (updates: DeviceUpdateInput, reason: string) => Promise<void>;
};

function resolveActiveTab(pathname: string): InventoryTabId {
  if (pathname.includes("/movimientos")) {
    return "movimientos";
  }
  if (pathname.includes("/proveedores")) {
    return "proveedores";
  }
  if (pathname.includes("/alertas")) {
    return "alertas";
  }
  return "productos";
}

export function useInventoryLayoutState(): InventoryLayoutState {
  const navigate = useNavigate();
  const location = useLocation();
  const { globalSearchTerm, setGlobalSearchTerm, pushToast, setError } = useDashboard();
  const inventoryModule = useInventoryModule();
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
    stockByCategory,
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
  } = inventoryModule;

  const [inventoryQuery, setInventoryQuery] = useState("");
  const [estadoFilter, setEstadoFilter] = useState<Device["estado_comercial"] | "TODOS">("TODOS");
  const [editingDevice, setEditingDevice] = useState<Device | null>(null);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [thresholdDraft, setThresholdDraft] = useState(lowStockThreshold);
  const [isSavingThreshold, setIsSavingThreshold] = useState(false);
  const [exportingCatalog, setExportingCatalog] = useState(false);
  const [importingCatalog, setImportingCatalog] = useState(false);
  const [catalogFile, setCatalogFile] = useState<File | null>(null);
  const [lastImportSummary, setLastImportSummary] = useState<DeviceImportSummary | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const smartImport = useSmartImportManager({
    smartImportInventory,
    fetchSmartImportHistory,
    fetchIncompleteDevices,
    refreshSummary,
    selectedStore,
    selectedStoreId,
    pushToast,
    setError,
  });

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
    smartFileInputRef,
    handleSmartOverrideChange,
    handleSmartPreview,
    handleSmartCommit,
    resetSmartImportContext,
  } = smartImport;

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

  const highlightedDevices = useMemo(
    () => new Set(lowStockDevices.map((entry) => entry.device_id)),
    [lowStockDevices],
  );

  const categoryChartData = useMemo(
    () =>
      stockByCategory.slice(0, 6).map((entry) => ({
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
      const deviceFilters: DeviceListFilters = {};
      const normalizedQuery = inventoryQuery.trim();
      if (normalizedQuery) {
        deviceFilters.search = normalizedQuery;
      }
      if (estadoFilter !== "TODOS") {
        deviceFilters.estado = estadoFilter;
      }
      await requestSnapshotDownload(
        (reason) => exportCatalogCsv(deviceFilters, reason),
        "Catálogo CSV exportado",
      );
    } finally {
      setExportingCatalog(false);
    }
  }, [estadoFilter, exportCatalogCsv, inventoryQuery, pushToast, requestSnapshotDownload, selectedStoreId, setError]);

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
    lowStockThreshold,
    pushToast,
    selectedStoreId,
    setError,
    thresholdDraft,
    updateLowStockThreshold,
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
        // Errores gestionados en el contexto de dashboard.
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
    const header = "%PDF-1.4\n";
    const objects = [
      "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
      "2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj",
      "3 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 595 842] /Contents 5 0 R >> endobj",
      "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
    ];
    const stream = streamLines.join("\n");
    const contentObject = `5 0 obj << /Length ${stream.length + 1} >> stream\n${stream}\nendstream endobj`;
    const body = `${objects.join("\n")}\n${contentObject}`;
    const offset1 = header.length;
    const offset2 = offset1 + objects[0].length + 1;
    const offset3 = offset2 + objects[1].length + 1;
    const offset4 = offset3 + objects[2].length + 1;
    const offset5 = offset4 + objects[3].length + 1;
    const xref = `xref\n0 6\n0000000000 65535 f \n${offset1.toString().padStart(10, "0")} 00000 n \n${offset2
      .toString()
      .padStart(10, "0")} 00000 n \n${offset3.toString().padStart(10, "0")} 00000 n \n${offset4
      .toString()
      .padStart(10, "0")} 00000 n \n${offset5.toString().padStart(10, "0")} 00000 n \n`;
    const xrefPosition = header.length + body.length + 1;
    const trailer = `trailer << /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefPosition}\n%%EOF`;
    return new Blob([header, body, "\n", xref, trailer], { type: "application/pdf" });
  }, []);

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

  const resolveLowStockSeverity = useCallback((quantity: number): "critical" | "warning" | "notice" => {
    if (quantity <= 1) {
      return "critical";
    }
    if (quantity <= 3) {
      return "warning";
    }
    return "notice";
  }, []);

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
  }, [lowStockDevices, resolveLowStockSeverity]);

  const statusCards = useMemo<StatusCard[]>(() => {
    const refreshBadge = lastInventoryRefresh
      ? { tone: "success", text: "Auto" }
      : { tone: "warning", text: "Sin datos" };

    const versionBadge = updateStatus?.is_update_available
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
    stores.length,
    totalDevices,
    totalItems,
    totalValue,
    updateStatus,
  ]);

  let moduleStatus: "ok" | "warning" | "critical" = "ok";
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

  const activeTab = resolveActiveTab(location.pathname);

  const tabOptions = useMemo(
    () =>
      INVENTORY_TABS.map((tab) => ({
        id: tab.id,
        label: tab.label,
        icon: tab.icon,
      })),
    [],
  );

  const handleTabChange = useCallback(
    (tabId: InventoryTabId) => {
      const target = INVENTORY_TABS.find((tab) => tab.id === tabId);
      if (!target) {
        return;
      }
      navigate(target.path, { replace: false });
    },
    [navigate],
  );

  const contextValue = useMemo<InventoryLayoutContextValue>(
    () => ({
      module: inventoryModule,
      smartImport,
      search: {
        inventoryQuery,
        setInventoryQuery,
        estadoFilter,
        setEstadoFilter,
        filteredDevices,
        highlightedDeviceIds: highlightedDevices,
      },
      editing: {
        editingDevice,
        openEditDialog: (device: Device) => {
          setEditingDevice(device);
          setIsEditDialogOpen(true);
        },
        closeEditDialog,
        isEditDialogOpen,
        handleSubmitDeviceUpdates,
      },
      metrics: {
        statusCards,
        storeValuationSnapshot,
        lastBackup,
        lastRefreshDisplay,
        totalCategoryUnits,
        categoryChartData,
        moduleStatus,
        moduleStatusLabel,
        lowStockStats,
      },
      downloads: {
        triggerRefreshSummary,
        triggerDownloadReport,
        triggerDownloadCsv,
        requestDownloadWithReason: requestSnapshotDownload,
        triggerExportCatalog,
        triggerImportCatalog,
        downloadSmartResultCsv,
        downloadSmartResultPdf,
        triggerRefreshSupplierOverview,
        triggerRefreshRecentMovements,
      },
      catalog: {
        catalogFile,
        setCatalogFile,
        importingCatalog,
        exportingCatalog,
        lastImportSummary,
        fileInputRef,
      },
      alerts: {
        thresholdDraft,
        setThresholdDraft,
        updateThresholdDraftValue,
        handleSaveThreshold,
        isSavingThreshold,
      },
      helpers: {
        storeNameById,
        resolvePendingFields,
        resolveLowStockSeverity,
      },
    }),
    [
      inventoryModule,
      smartImport,
      inventoryQuery,
      estadoFilter,
      filteredDevices,
      highlightedDevices,
      editingDevice,
      closeEditDialog,
      isEditDialogOpen,
      handleSubmitDeviceUpdates,
      statusCards,
      storeValuationSnapshot,
      lastBackup,
      lastRefreshDisplay,
      totalCategoryUnits,
      categoryChartData,
      moduleStatus,
      moduleStatusLabel,
      lowStockStats,
      triggerRefreshSummary,
      triggerDownloadReport,
      triggerDownloadCsv,
      requestSnapshotDownload,
      triggerExportCatalog,
      triggerImportCatalog,
      downloadSmartResultCsv,
      downloadSmartResultPdf,
      triggerRefreshSupplierOverview,
      triggerRefreshRecentMovements,
      catalogFile,
      importingCatalog,
      exportingCatalog,
      lastImportSummary,
      fileInputRef,
      thresholdDraft,
      updateThresholdDraftValue,
      handleSaveThreshold,
      isSavingThreshold,
      storeNameById,
      resolvePendingFields,
      resolveLowStockSeverity,
    ],
  );

  return {
    contextValue,
    tabOptions,
    activeTab,
    handleTabChange,
    moduleStatus,
    moduleStatusLabel,
    loading,
    editingDevice,
    isEditDialogOpen,
    closeEditDialog,
    handleSubmitDeviceUpdates,
  };
}

