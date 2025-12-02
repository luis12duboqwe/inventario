import React from "react";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import TransferOrders from "../components/TransferOrders";

export default function OperationsTransfers() {
  const { token, stores, selectedStoreId, refreshInventoryAfterTransfer } = useDashboard();

  return (
    <TransferOrders
      token={token}
      stores={stores}
      defaultOriginId={selectedStoreId}
      onRefreshInventory={refreshInventoryAfterTransfer}
    />
  );
}
