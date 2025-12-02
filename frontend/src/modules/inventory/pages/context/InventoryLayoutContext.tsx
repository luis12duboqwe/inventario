import { useInventorySearch } from "./InventorySearchContext";
import { useInventoryMetrics } from "./InventoryMetricsContext";
import { useInventoryActions } from "./InventoryActionsContext";

// Re-export types for backward compatibility
export * from "./types";
export * from "./InventorySearchContext";
export * from "./InventoryMetricsContext";
export * from "./InventoryActionsContext";

// Deprecated: Use specific hooks instead
export function useInventoryLayout() {
  const search = useInventorySearch();
  const metrics = useInventoryMetrics();
  const actions = useInventoryActions();

  return {
    ...actions,
    search,
    metrics,
  };
}

// Deprecated: No longer used as a single provider
const InventoryLayoutContext = { Provider: null };
export default InventoryLayoutContext;
