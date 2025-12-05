import { useQuery } from "@tanstack/react-query";
import { inventoryService } from "../../services/inventoryService";

export function useSupplierBatchOverview(token: string, storeId: number | null) {
  return useQuery({
    queryKey: ["supplierBatchOverview", storeId],
    queryFn: () => {
      if (!storeId) return [];
      return inventoryService.fetchSupplierBatchOverview(token, storeId);
    },
    enabled: !!storeId && !!token,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}
