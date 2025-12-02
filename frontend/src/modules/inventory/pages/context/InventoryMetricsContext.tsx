import { createContext, useContext } from "react";
import type { StatusCard, InventoryModuleState } from "./types";
import type { ModuleStatus } from "../../../../shared/components/ModuleHeader";

export type InventoryMetricsContextValue = {
  statusCards: StatusCard[];
  storeValuationSnapshot: InventoryModuleState["storeValuationSnapshot"];
  lastBackup: InventoryModuleState["backupHistory"][number] | null;
  lastRefreshDisplay: string;
  totalCategoryUnits: number;
  categoryChartData: Array<{ label: string; value: number }>;
  moduleStatus: ModuleStatus;
  moduleStatusLabel: string;
  lowStockStats: { critical: number; warning: number };
};

export const InventoryMetricsContext = createContext<InventoryMetricsContextValue | undefined>(
  undefined,
);

export function useInventoryMetrics(): InventoryMetricsContextValue {
  const context = useContext(InventoryMetricsContext);
  if (!context) {
    throw new Error("useInventoryMetrics must be used within InventoryMetricsContext.Provider");
  }
  return context;
}
