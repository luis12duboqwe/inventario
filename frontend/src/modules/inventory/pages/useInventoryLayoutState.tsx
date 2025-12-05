import { useCallback, useEffect, useMemo, type ReactNode } from "react";
import {
  Building2,
  Cog,
  DollarSign,
  RefreshCcw,
  ShieldCheck,
  Smartphone,
  Boxes,
} from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import type { Device, DeviceUpdateInput } from "@api/inventory";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import { useInventoryModule } from "../hooks/useInventoryModule";
import { useSmartImportManager } from "./hooks/useSmartImportManager";
import { safeArray } from "@/utils/safeValues";
import type { StatusBadge, StatusCard } from "./context/InventoryLayoutContext";

// New Context Types
import type { InventorySearchContextValue } from "./context/InventorySearchContext";
import type { InventoryMetricsContextValue } from "./context/InventoryMetricsContext";
import type { InventoryActionsContextValue } from "./context/InventoryActionsContext";

// Extracted Hooks
import { useInventoryTabs, type InventoryTabId } from "./hooks/useInventoryTabs";
import { useInventoryEdit } from "./hooks/useInventoryEdit";
import { useInventoryStatus } from "./hooks/useInventoryStatus";
import { useInventoryVariants } from "./hooks/useInventoryVariants";
import { useInventoryBundles } from "./hooks/useInventoryBundles";
import { useInventoryLabeling } from "./hooks/useInventoryLabeling";
import { useInventoryFiltering } from "./hooks/useInventoryFiltering";
import { useInventoryDownloads } from "./hooks/useInventoryDownloads";
import { useInventoryAlerts } from "./hooks/useInventoryAlerts";

export type { InventoryTabId };

export type InventoryLayoutContextValue = {
  module: InventoryActionsContextValue["module"];
  smartImport: InventoryActionsContextValue["smartImport"];
  search: InventorySearchContextValue;
  editing: InventoryActionsContextValue["editing"];
  metrics: InventoryMetricsContextValue;
  downloads: InventoryActionsContextValue["downloads"];
  catalog: InventoryActionsContextValue["catalog"];
  alerts: InventoryActionsContextValue["alerts"];
  helpers: InventoryActionsContextValue["helpers"];
  labeling: InventoryActionsContextValue["labeling"];
  reservations: InventoryActionsContextValue["reservations"];
  variants: InventoryActionsContextValue["variants"];
  bundles: InventoryActionsContextValue["bundles"];
};

export type InventoryLayoutState = {
  // Split Context Values
  searchValue: InventorySearchContextValue;
  metricsValue: InventoryMetricsContextValue;
  actionsValue: InventoryActionsContextValue;

  // Legacy Context Value (constructed from split values for backward compat if needed)
  contextValue: InventoryLayoutContextValue;

  // Page State
  tabOptions: Array<{ id: string; label: string; icon: ReactNode; href: string }>;
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

export function useInventoryLayoutState(): InventoryLayoutState {
  const navigate = useNavigate();
  const location = useLocation();
  const { enablePriceLists, pushToast, setError } = useDashboard();
  const inventoryModule = useInventoryModule();
  const {
    stores,
    selectedStoreId,
    selectedStore,
    devices,
    loading,
    totalDevices,
    totalItems,
    totalValue,
    formatCurrency,
    lowStockDevices,
    backupHistory,
    updateStatus,
    lastInventoryRefresh,
    downloadInventoryReport,
    downloadInventoryCsv,
    exportCatalogCsv,
    importCatalogCsv,
    refreshSupplierBatchOverview,
    stockByCategory,
    refreshRecentMovements,
    lowStockThreshold,
    updateLowStockThreshold,
    refreshSummary,
    storeValuationSnapshot,
    smartImportInventory,
    fetchSmartImportHistory,
    fetchIncompleteDevices,
    reservations,
    reservationsMeta,
    reservationsLoading,
    reservationsIncludeExpired,
    setReservationsIncludeExpired,
    refreshReservations: refreshInventoryReservations,
    createReservation: createInventoryReservation,
    renewReservation: renewInventoryReservation,
    cancelReservation: cancelInventoryReservation,
    expiringReservations,
  } = inventoryModule;

  // --- Extracted Hooks ---
  const { tabs, activeTab, handleTabChange } = useInventoryTabs(enablePriceLists);

  const {
    editingDevice,
    isEditDialogOpen,
    openEditDialog,
    closeEditDialog,
    handleSubmitDeviceUpdates: handleEditSubmit,
  } = useInventoryEdit(
    inventoryModule.token,
    selectedStoreId,
    refreshSummary,
    (msg, type) => pushToast({ message: msg, variant: type }),
    setError,
  );

  const { status: computedModuleStatus, label: computedModuleStatusLabel } = useInventoryStatus(
    lowStockDevices.length,
    totalDevices,
    reservationsMeta ? { active_count: reservationsMeta.total } : undefined,
  );

  const {
    variants,
    variantsLoading,
    variantsIncludeInactive,
    setVariantsIncludeInactive,
    refreshVariants,
    handleCreateVariant,
    handleUpdateVariant,
    handleArchiveVariant,
  } = useInventoryVariants({
    token: inventoryModule.token,
    selectedStoreId: inventoryModule.selectedStoreId,
    enableVariants: inventoryModule.enableVariants,
    pushToast,
    setError,
  });

  const {
    bundles,
    bundlesLoading,
    bundlesIncludeInactive,
    setBundlesIncludeInactive,
    refreshBundles,
    handleCreateBundle,
    handleUpdateBundle,
    handleArchiveBundle,
  } = useInventoryBundles({
    token: inventoryModule.token,
    selectedStoreId: inventoryModule.selectedStoreId,
    enableBundles: inventoryModule.enableBundles,
    pushToast,
    setError,
  });

  const {
    inventoryQuery,
    setInventoryQuery,
    estadoFilter,
    setEstadoFilter,
    filteredDevices,
    highlightedDevices,
  } = useInventoryFiltering(devices, lowStockDevices, selectedStoreId);

  const {
    exportingCatalog,
    importingCatalog,
    catalogFile,
    setCatalogFile,
    lastImportSummary,
    fileInputRef,
    handleDownloadReportClick,
    handleDownloadCsvClick,
    handleExportCatalogClick,
    handleImportCatalogSubmit,
  } = useInventoryDownloads({
    selectedStore,
    selectedStoreId,
    inventoryQuery,
    estadoFilter,
    pushToast,
    setError,
    downloadInventoryReport,
    downloadInventoryCsv,
    exportCatalogCsv,
    importCatalogCsv,
  });

  const {
    thresholdDraft,
    setThresholdDraft,
    updateThresholdDraftValue,
    handleSaveThreshold,
    isSavingThreshold,
  } = useInventoryAlerts(
    lowStockThreshold,
    selectedStoreId,
    updateLowStockThreshold,
    pushToast,
    setError,
  );

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

  // --- Effects ---

  useEffect(() => {
    if (!enablePriceLists && location.pathname.includes("/listas")) {
      navigate("productos", { replace: true });
    }
  }, [enablePriceLists, location.pathname, navigate]);

  // --- Derived State ---

  const lastBackup = backupHistory.at(0) ?? null;
  const lastRefreshDisplay = lastInventoryRefresh
    ? lastInventoryRefresh.toLocaleString("es-HN")
    : "En espera de la primera actualización";

  const storeNameById = useMemo(() => {
    const mapping = new Map<number, string>();
    stores.forEach((store) => mapping.set(store.id, store.name));
    return mapping;
  }, [stores]);

  const {
    labelingDevice,
    labelingStoreId,
    labelingStoreName,
    isLabelPrinterOpen,
    openLabelPrinter,
    closeLabelPrinter,
  } = useInventoryLabeling(selectedStore, selectedStoreId, storeNameById);

  const categoryChartData = useMemo(
    () =>
      safeArray(stockByCategory)
        .slice(0, 6)
        .map((entry) => ({
          label: entry.label || "Sin categoría",
          value: entry.value,
        })),
    [stockByCategory],
  );

  const totalCategoryUnits = useMemo(
    () => categoryChartData.reduce((total, entry) => total + entry.value, 0),
    [categoryChartData],
  );

  const resolveLowStockSeverity = useCallback(
    (quantity: number): "critical" | "warning" | "notice" => {
      if (quantity <= 1) {
        return "critical";
      }
      if (quantity <= 3) {
        return "warning";
      }
      return "notice";
    },
    [],
  );

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
    const refreshBadge: StatusBadge = lastInventoryRefresh
      ? { tone: "success", text: "Auto" }
      : { tone: "warning", text: "Sin datos" };

    const versionBadge: StatusBadge = updateStatus?.is_update_available
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
          ? new Date(lastBackup.executed_at).toLocaleString("es-HN")
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
          ? lastInventoryRefresh.toLocaleTimeString("es-HN")
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

  // Use computed status from hook, but override if loading (as per original logic)
  let moduleStatus = computedModuleStatus;
  let moduleStatusLabel = computedModuleStatusLabel;

  if (loading) {
    moduleStatus = "warning";
    moduleStatusLabel = "Actualizando inventario";
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

  const tabOptions = useMemo(
    () =>
      tabs.map((tab) => ({
        id: tab.id,
        label: tab.label,
        icon: tab.icon,
        href: tab.path,
      })),
    [tabs],
  );

  // Note: handleSubmitDeviceUpdates is now handled by useInventoryEdit hook (handleEditSubmit)
  // We need to wrap it to include the smartImport refresh logic that was in the original file
  const handleSubmitDeviceUpdates = useCallback(
    async (updates: DeviceUpdateInput, reason: string) => {
      await handleEditSubmit(updates, reason);
      // These were called after update in the original file
      await smartImport.refreshPendingDevices();
      void refreshSummary();
    },
    [handleEditSubmit, smartImport, refreshSummary],
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

  // --- Split Context Values ---

  const searchValue = useMemo<InventorySearchContextValue>(
    () => ({
      inventoryQuery,
      setInventoryQuery,
      estadoFilter,
      setEstadoFilter,
      filteredDevices,
      highlightedDeviceIds: highlightedDevices,
    }),
    [
      inventoryQuery,
      setInventoryQuery,
      estadoFilter,
      setEstadoFilter,
      filteredDevices,
      highlightedDevices,
    ],
  );

  const metricsValue = useMemo<InventoryMetricsContextValue>(
    () => ({
      statusCards,
      storeValuationSnapshot,
      lastBackup,
      lastRefreshDisplay,
      totalCategoryUnits,
      categoryChartData,
      moduleStatus,
      moduleStatusLabel,
      lowStockStats,
    }),
    [
      statusCards,
      storeValuationSnapshot,
      lastBackup,
      lastRefreshDisplay,
      totalCategoryUnits,
      categoryChartData,
      moduleStatus,
      moduleStatusLabel,
      lowStockStats,
    ],
  );

  const actionsValue = useMemo<InventoryActionsContextValue>(
    () => ({
      module: inventoryModule,
      smartImport,
      editing: {
        editingDevice,
        openEditDialog,
        closeEditDialog,
        isEditDialogOpen,
        handleSubmitDeviceUpdates,
      },
      downloads: {
        triggerRefreshSummary,
        triggerDownloadReport,
        triggerDownloadCsv,
        triggerExportCatalog,
        triggerImportCatalog,
        downloadSmartResultCsv: smartImport.downloadSmartResultCsv,
        downloadSmartResultPdf: smartImport.downloadSmartResultPdf,
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
      labeling: {
        open: isLabelPrinterOpen,
        device: labelingDevice,
        storeId: labelingStoreId,
        storeName: labelingStoreName ?? undefined,
        openLabelPrinter,
        closeLabelPrinter,
      },
      reservations: {
        items: reservations,
        meta: reservationsMeta,
        loading: reservationsLoading,
        includeExpired: reservationsIncludeExpired,
        setIncludeExpired: setReservationsIncludeExpired,
        refresh: refreshInventoryReservations,
        create: createInventoryReservation,
        renew: renewInventoryReservation,
        cancel: cancelInventoryReservation,
        expiringSoon: expiringReservations,
      },
      variants: {
        enabled: inventoryModule.enableVariants,
        loading: variantsLoading,
        includeInactive: variantsIncludeInactive,
        setIncludeInactive: setVariantsIncludeInactive,
        items: variants,
        refresh: refreshVariants,
        create: handleCreateVariant,
        update: handleUpdateVariant,
        archive: handleArchiveVariant,
      },
      bundles: {
        enabled: inventoryModule.enableBundles,
        loading: bundlesLoading,
        includeInactive: bundlesIncludeInactive,
        setIncludeInactive: setBundlesIncludeInactive,
        items: bundles,
        refresh: refreshBundles,
        create: handleCreateBundle,
        update: handleUpdateBundle,
        archive: handleArchiveBundle,
      },
    }),
    [
      inventoryModule,
      smartImport,
      editingDevice,
      openEditDialog,
      closeEditDialog,
      isEditDialogOpen,
      handleSubmitDeviceUpdates,
      triggerRefreshSummary,
      triggerDownloadReport,
      triggerDownloadCsv,
      triggerExportCatalog,
      triggerImportCatalog,
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
      reservations,
      reservationsMeta,
      reservationsLoading,
      reservationsIncludeExpired,
      setReservationsIncludeExpired,
      refreshInventoryReservations,
      createInventoryReservation,
      renewInventoryReservation,
      cancelInventoryReservation,
      expiringReservations,
      isLabelPrinterOpen,
      labelingDevice,
      labelingStoreId,
      labelingStoreName,
      openLabelPrinter,
      closeLabelPrinter,
      variants,
      variantsLoading,
      variantsIncludeInactive,
      refreshVariants,
      handleCreateVariant,
      handleUpdateVariant,
      handleArchiveVariant,
      setVariantsIncludeInactive,
      bundles,
      bundlesLoading,
      bundlesIncludeInactive,
      refreshBundles,
      handleCreateBundle,
      handleUpdateBundle,
      handleArchiveBundle,
      setBundlesIncludeInactive,
      setCatalogFile,
      setThresholdDraft,
    ],
  );

  // Construct legacy context value from split values
  const contextValue = useMemo<InventoryLayoutContextValue>(
    () => ({
      module: actionsValue.module,
      smartImport: actionsValue.smartImport,
      search: searchValue,
      editing: actionsValue.editing,
      metrics: metricsValue,
      downloads: actionsValue.downloads,
      catalog: actionsValue.catalog,
      alerts: actionsValue.alerts,
      helpers: actionsValue.helpers,
      labeling: actionsValue.labeling,
      reservations: actionsValue.reservations,
      variants: actionsValue.variants,
      bundles: actionsValue.bundles,
    }),
    [searchValue, metricsValue, actionsValue],
  );

  return {
    searchValue,
    metricsValue,
    actionsValue,
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
