import { useDashboard } from "../../dashboard/context/DashboardContext";

export function useRepairsModule() {
  const dashboard = useDashboard();

  return {
    token: dashboard.token,
    stores: dashboard.stores,
    selectedStoreId: dashboard.selectedStoreId,
    setSelectedStoreId: dashboard.setSelectedStoreId,
    refreshInventoryAfterTransfer: dashboard.refreshInventoryAfterTransfer,
    enablePurchasesSales: dashboard.enablePurchasesSales,
  };
}
