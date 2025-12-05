import { useCallback } from "react";
import { inventoryService } from "../../services/inventoryService";
import {
  InventoryCurrentFilters,
  InventoryValueFilters,
  InventoryMovementsFilters,
  InventoryTopProductsFilters,
  InactiveProductsFilters,
  SyncDiscrepancyFilters,
} from "@api/inventory";

export function useInventoryReports(token: string) {
  const fetchInventoryCurrentReport = useCallback(
    (filters: InventoryCurrentFilters = {}) =>
      inventoryService.fetchInventoryCurrentReport(token, filters),
    [token],
  );

  const fetchInventoryValueReport = useCallback(
    (filters: InventoryValueFilters = {}) =>
      inventoryService.fetchInventoryValueReport(token, filters),
    [token],
  );

  const fetchInactiveProductsReport = useCallback(
    (filters: InactiveProductsFilters = {}) =>
      inventoryService.fetchInactiveProductsReport(token, filters),
    [token],
  );

  const fetchInventoryMovementsReport = useCallback(
    (filters: InventoryMovementsFilters = {}) =>
      inventoryService.fetchInventoryMovementsReport(token, filters),
    [token],
  );

  const fetchTopProductsReport = useCallback(
    (filters: InventoryTopProductsFilters = {}) =>
      inventoryService.fetchTopProductsReport(token, filters),
    [token],
  );

  const fetchSyncDiscrepancyReport = useCallback(
    (filters: SyncDiscrepancyFilters = {}) =>
      inventoryService.fetchSyncDiscrepancyReport(token, filters),
    [token],
  );

  return {
    fetchInventoryCurrentReport,
    fetchInventoryValueReport,
    fetchInactiveProductsReport,
    fetchInventoryMovementsReport,
    fetchTopProductsReport,
    fetchSyncDiscrepancyReport,
  };
}
