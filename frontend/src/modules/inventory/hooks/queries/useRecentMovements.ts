import { useQuery } from "@tanstack/react-query";
import { inventoryService } from "../../services/inventoryService";
import { InventoryMovementsFilters } from "@api/inventory";

export function useRecentMovements(token: string, storeId: number | null, lastRefresh?: number) {
  return useQuery({
    queryKey: ["recentMovements", storeId, lastRefresh],
    queryFn: async () => {
      const filters: InventoryMovementsFilters = {};
      if (storeId) {
        filters.storeIds = [storeId];
      }
      const now = new Date();
      const pastDate = new Date(now);
      pastDate.setDate(now.getDate() - 14);
      filters.dateFrom = pastDate.toISOString();
      filters.dateTo = now.toISOString();

      const report = await inventoryService.fetchInventoryMovementsReport(token, filters);
      return report.movimientos.slice(0, 8);
    },
    enabled: !!token,
    staleTime: 1000 * 60, // 1 minute
  });
}
