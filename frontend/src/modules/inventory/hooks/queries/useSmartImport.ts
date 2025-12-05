import { useQuery } from "@tanstack/react-query";
import { inventoryService } from "../../services/inventoryService";

export function useSmartImportHistory(token: string, limit = 10) {
  return useQuery({
    queryKey: ["smartImportHistory", limit],
    queryFn: () => inventoryService.fetchSmartImportHistory(token, limit),
    enabled: !!token,
  });
}

export function useIncompleteDevices(token: string, storeId?: number, limit = 100) {
  return useQuery({
    queryKey: ["incompleteDevices", storeId, limit],
    queryFn: () => inventoryService.fetchIncompleteDevices(token, storeId, limit),
    enabled: !!token,
  });
}
