import { createContext, useContext } from "react";

import type { Store } from "../../../../api";
import type { ModuleStatus } from "../../../../shared/components/ModuleHeader";

type RepairsLayoutContextValue = {
  token: string;
  stores: Store[];
  selectedStoreId: number | null;
  setSelectedStoreId: (storeId: number | null) => void;
  onInventoryRefresh?: () => void;
  moduleStatus: ModuleStatus;
  moduleStatusLabel: string;
  setModuleStatus: (status: ModuleStatus, label: string) => void;
};

const RepairsLayoutContext = createContext<RepairsLayoutContextValue | undefined>(undefined);

function useRepairsLayout() {
  const context = useContext(RepairsLayoutContext);
  if (!context) {
    throw new Error("useRepairsLayout debe usarse dentro de RepairsLayoutContext.Provider");
  }
  return context;
}

export type { RepairsLayoutContextValue };
export { RepairsLayoutContext, useRepairsLayout };
export default RepairsLayoutContext;
