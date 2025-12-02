import React from "react";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import Returns from "../components/Returns";

export default function OperationsReturns() {
  const { token, stores, selectedStoreId, refreshInventoryAfterTransfer } = useDashboard();

  return (
    <Returns
      token={token}
      stores={stores}
      defaultStoreId={selectedStoreId}
      onInventoryRefresh={refreshInventoryAfterTransfer}
    />
  );
}
