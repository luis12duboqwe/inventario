import { useDashboard } from "../../dashboard/context/DashboardContext";
import { inventoryService } from "../services/inventoryService";

export function useInventoryModule() {
  const dashboard = useDashboard();

  const downloadInventoryReport = () => inventoryService.downloadInventoryReport(dashboard.token);

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
    backupHistory: dashboard.backupHistory,
    updateStatus: dashboard.updateStatus,
    lastInventoryRefresh: dashboard.lastInventoryRefresh,
    downloadInventoryReport,
  };
}
