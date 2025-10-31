import { useDashboard } from "../../dashboard/context/DashboardContext";

export function useOperationsModule() {
  const dashboard = useDashboard();

  return {
    token: dashboard.token,
    stores: dashboard.stores,
    selectedStoreId: dashboard.selectedStoreId,
    enablePurchasesSales: dashboard.enablePurchasesSales,
    enableTransfers: dashboard.enableTransfers,
    refreshInventoryAfterTransfer: dashboard.refreshInventoryAfterTransfer,
  };
}
