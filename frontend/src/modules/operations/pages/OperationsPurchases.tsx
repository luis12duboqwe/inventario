import React from "react";
import Purchases from "../components/Purchases";
import { useDashboard } from "../../dashboard/context/DashboardContext";

export default function OperationsPurchases() {
  const { token, stores, selectedStoreId, refreshInventoryAfterTransfer } = useDashboard();

  return (
    <Purchases
      token={token}
      stores={stores}
      defaultStoreId={selectedStoreId}
      onInventoryRefresh={refreshInventoryAfterTransfer}
    />
  );
}
