import { createContext, useContext } from "react";
import type { Device } from "@api/inventory";

export type InventorySearchContextValue = {
  inventoryQuery: string;
  setInventoryQuery: (value: string) => void;
  estadoFilter: Device["estado_comercial"] | "TODOS";
  setEstadoFilter: (value: Device["estado_comercial"] | "TODOS") => void;
  filteredDevices: Device[];
  highlightedDeviceIds: Set<number>;
};

export const InventorySearchContext = createContext<InventorySearchContextValue | undefined>(
  undefined,
);

export function useInventorySearch(): InventorySearchContextValue {
  const context = useContext(InventorySearchContext);
  if (!context) {
    throw new Error("useInventorySearch must be used within InventorySearchContext.Provider");
  }
  return context;
}
