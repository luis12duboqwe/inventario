import { useCallback, useEffect, useState } from "react";

import type { SupplierBatchOverviewItem } from "../../../api";
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
    supplierBatchOverview,
    supplierBatchLoading,
    refreshSupplierBatchOverview,
    lowStockThreshold: dashboard.currentLowStockThreshold,
    updateLowStockThreshold: dashboard.updateLowStockThreshold,
    refreshSummary: dashboard.refreshSummary,
  };
}
