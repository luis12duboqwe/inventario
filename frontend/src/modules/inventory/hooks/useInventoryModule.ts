import { useCallback, useEffect, useMemo, useState } from "react";

import type {
  InventoryCurrentFilters,
  InventoryMovementsFilters,
  InventoryTopProductsFilters,
  InventoryValueFilters,
  SupplierBatchOverviewItem,
} from "../../../api";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import { inventoryService } from "../services/inventoryService";

export function useInventoryModule() {
  const dashboard = useDashboard();

  const [supplierBatchOverview, setSupplierBatchOverview] = useState<
    SupplierBatchOverviewItem[]
  >([]);
  const [supplierBatchLoading, setSupplierBatchLoading] = useState(false);

  const refreshSupplierBatchOverview = useCallback(async () => {
    if (!dashboard.selectedStoreId) {
      setSupplierBatchOverview([]);
      return;
    }
    try {
      setSupplierBatchLoading(true);
      const data = await inventoryService.fetchSupplierBatchOverview(
        dashboard.token,
        dashboard.selectedStoreId,
      );
      setSupplierBatchOverview(data);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible consultar los lotes recientes por proveedor.";
      dashboard.setError(message);
      dashboard.pushToast({ message, variant: "error" });
    } finally {
      setSupplierBatchLoading(false);
    }
  }, [
    dashboard.pushToast,
    dashboard.selectedStoreId,
    dashboard.setError,
    dashboard.token,
  ]);

  useEffect(() => {
    void refreshSupplierBatchOverview();
  }, [refreshSupplierBatchOverview]);

  const downloadInventoryReport = (reason: string) =>
    inventoryService.downloadInventoryReport(dashboard.token, reason);

  const downloadInventoryCsv = (reason: string) =>
    inventoryService.downloadInventoryCsv(dashboard.token, reason);

  const exportCatalogCsv = (filters: Parameters<typeof inventoryService.fetchDevices>[2], reason: string) => {
    if (!dashboard.selectedStoreId) {
      throw new Error("Selecciona una sucursal para exportar el catálogo");
    }
    return inventoryService.exportCatalogCsv(
      dashboard.token,
      dashboard.selectedStoreId,
      filters,
      reason,
    );
  };

  const importCatalogCsv = async (file: File, reason: string) => {
    if (!dashboard.selectedStoreId) {
      throw new Error("Selecciona una sucursal para importar productos");
    }
    const summary = await inventoryService.importCatalogCsv(
      dashboard.token,
      dashboard.selectedStoreId,
      file,
      reason,
    );
    await dashboard.refreshInventoryAfterTransfer();
    return summary;
  };

  const storeValuationSnapshot = useMemo(() => {
    if (!dashboard.selectedStoreId || !dashboard.selectedStore) {
      return null;
    }
    const summaryEntry = dashboard.summary.find(
      (entry) => entry.store_id === dashboard.selectedStoreId,
    );
    if (!summaryEntry) {
      return null;
    }
    const registeredValue = dashboard.selectedStore.inventory_value ?? 0;
    const calculatedValue = summaryEntry.total_value;
    const difference = calculatedValue - registeredValue;
    const differenceAbs = Math.abs(difference);
    const differencePercent =
      registeredValue === 0 ? null : (difference / registeredValue) * 100;

    return {
      storeId: dashboard.selectedStoreId,
      storeName: dashboard.selectedStore.name,
      registeredValue,
      calculatedValue,
      difference,
      differenceAbs,
      differencePercent,
      hasRelevantDifference: differenceAbs >= 1,
    };
  }, [dashboard.selectedStore, dashboard.selectedStoreId, dashboard.summary]);

  const fetchInventoryCurrentReport = useCallback(
    (filters: InventoryCurrentFilters = {}) =>
      inventoryService.fetchInventoryCurrentReport(dashboard.token, filters),
    [dashboard.token],
  );

  const fetchInventoryValueReport = useCallback(
    (filters: InventoryValueFilters = {}) =>
      inventoryService.fetchInventoryValueReport(dashboard.token, filters),
    [dashboard.token],
  );

  const fetchInventoryMovementsReport = useCallback(
    (filters: InventoryMovementsFilters = {}) =>
      inventoryService.fetchInventoryMovementsReport(dashboard.token, filters),
    [dashboard.token],
  );

  const fetchTopProductsReport = useCallback(
    (filters: InventoryTopProductsFilters = {}) =>
      inventoryService.fetchTopProductsReport(dashboard.token, filters),
    [dashboard.token],
  );

  const downloadInventoryValueCsv = useCallback(
    (reason: string, filters: InventoryValueFilters = {}) =>
      inventoryService.downloadInventoryValueCsv(dashboard.token, reason, filters),
    [dashboard.token],
  );

  const downloadInventoryMovementsCsv = useCallback(
    (reason: string, filters: InventoryMovementsFilters = {}) =>
      inventoryService.downloadInventoryMovementsCsv(dashboard.token, reason, filters),
    [dashboard.token],
  );

  const downloadTopProductsCsv = useCallback(
    (reason: string, filters: InventoryTopProductsFilters = {}) =>
      inventoryService.downloadTopProductsCsv(dashboard.token, reason, filters),
    [dashboard.token],
  );

  return {
    token: dashboard.token,
    enableCatalogPro: dashboard.enableCatalogPro,
    stores: dashboard.stores,
    selectedStoreId: dashboard.selectedStoreId,
    setSelectedStoreId: dashboard.setSelectedStoreId,
    selectedStore: dashboard.selectedStore,
    devices: dashboard.devices,
    loading: dashboard.loading,
    totalDevices: dashboard.totalDevices,
    totalItems: dashboard.totalItems,
    totalValue: dashboard.totalValue,
    formatCurrency: dashboard.formatCurrency,
    topStores: dashboard.topStores,
    lowStockDevices: dashboard.lowStockDevices,
    handleMovement: dashboard.handleMovement,
    handleDeviceUpdate: dashboard.handleDeviceUpdate,
    backupHistory: dashboard.backupHistory,
    updateStatus: dashboard.updateStatus,
    lastInventoryRefresh: dashboard.lastInventoryRefresh,
    downloadInventoryReport,
    downloadInventoryCsv,
    exportCatalogCsv,
    importCatalogCsv,
    supplierBatchOverview,
    supplierBatchLoading,
    refreshSupplierBatchOverview,
    lowStockThreshold: dashboard.currentLowStockThreshold,
    updateLowStockThreshold: dashboard.updateLowStockThreshold,
    refreshSummary: dashboard.refreshSummary,
    storeValuationSnapshot,
    fetchInventoryCurrentReport,
    fetchInventoryValueReport,
    fetchInventoryMovementsReport,
    fetchTopProductsReport,
    downloadInventoryValueCsv,
    downloadInventoryMovementsCsv,
    downloadTopProductsCsv,
  };
}
