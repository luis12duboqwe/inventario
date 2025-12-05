import { useMemo, useState, useEffect } from "react";

import type {
  InventoryCurrentFilters,
  InventoryMovementsFilters,
  InventoryTopProductsFilters,
  InventoryValueFilters,
  InventoryReservationInput,
  InventoryReservationRenewInput,
} from "@api/inventory";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import { inventoryService } from "../services/inventoryService";

// New hooks
import { useSupplierBatchOverview } from "./queries/useSupplierBatchOverview";
import { useRecentMovements } from "./queries/useRecentMovements";
import { useInventoryReservations } from "./queries/useInventoryReservations";
import { useInventoryReports } from "./queries/useInventoryReports";
import { useSmartImportHistory, useIncompleteDevices } from "./queries/useSmartImport";

export function useInventoryModule() {
  const dashboard = useDashboard();
  const { token, selectedStoreId, pushToast } = dashboard;
  const RESERVATION_PAGE_SIZE = 20;

  // --- Supplier Batches ---
  const {
    data: supplierBatchOverview = [],
    isLoading: supplierBatchLoading,
    refetch: refreshSupplierBatchOverview
  } = useSupplierBatchOverview(token, selectedStoreId);

  // --- Recent Movements ---
  const {
    data: recentMovements = [],
    isLoading: recentMovementsLoading,
    refetch: refreshRecentMovements
  } = useRecentMovements(token, selectedStoreId, dashboard.lastInventoryRefresh);

  // --- Reservations ---
  const [reservationsIncludeExpired, setReservationsIncludeExpired] = useState(false);
  // We need to manage page state here because it's UI state, not server state
  const [reservationsPage, setReservationsPage] = useState(1);

  const {
    data: reservationsData,
    isLoading: reservationsLoading,
    refetch: refreshReservations,
    createReservation: createReservationMutation,
    renewReservation: renewReservationMutation,
    cancelReservation: cancelReservationMutation,
  } = useInventoryReservations(
    token,
    selectedStoreId,
    reservationsPage,
    RESERVATION_PAGE_SIZE,
    reservationsIncludeExpired
  );

  const reservations = useMemo(() => reservationsData?.items || [], [reservationsData]);
  const reservationsMeta = {
    page: reservationsData?.page || 1,
    size: reservationsData?.size || RESERVATION_PAGE_SIZE,
    total: reservationsData?.total || 0,
    pages: reservationsData?.pages || 0,
  };

  // Wrappers for mutations to match existing interface and handle toasts/errors
  const createReservation = async (
    input: Omit<InventoryReservationInput, "store_id">,
    reason: string,
  ) => {
    try {
      await createReservationMutation({ input, reason });
      pushToast({ message: "Reserva creada exitosamente.", variant: "success" });
    } catch (error) {
      const message = error instanceof Error ? error.message : "No fue posible crear la reserva.";
      pushToast({ message, variant: "error" });
      throw error;
    }
  };

  const renewReservation = async (
    reservationId: number,
    input: InventoryReservationRenewInput,
    reason: string,
  ) => {
    try {
      await renewReservationMutation({ reservationId, input, reason });
      pushToast({ message: "Reserva renovada correctamente.", variant: "success" });
    } catch (error) {
      const message = error instanceof Error ? error.message : "No fue posible renovar la reserva.";
      pushToast({ message, variant: "error" });
      throw error;
    }
  };

  const cancelReservation = async (reservationId: number, reason: string) => {
    try {
      await cancelReservationMutation({ reservationId, reason });
      pushToast({ message: "Reserva cancelada y devuelta al inventario.", variant: "success" });
    } catch (error) {
      const message = error instanceof Error ? error.message : "No fue posible cancelar la reserva.";
      pushToast({ message, variant: "error" });
      throw error;
    }
  };

  // --- Reports ---
  const {
    fetchInventoryCurrentReport,
    fetchInventoryValueReport,
    fetchInactiveProductsReport,
    fetchInventoryMovementsReport,
    fetchTopProductsReport,
    fetchSyncDiscrepancyReport,
  } = useInventoryReports(token);

  // --- Smart Import ---
  const { refetch: fetchSmartImportHistory } = useSmartImportHistory(token);
  const { refetch: fetchIncompleteDevices } = useIncompleteDevices(token, selectedStoreId);

  // --- Legacy / Manual implementations (kept for compatibility or specific logic) ---

  const downloadInventoryReport = (reason: string) =>
    inventoryService.downloadInventoryReport(dashboard.token, reason);

  const downloadInventoryCsv = (reason: string) =>
    inventoryService.downloadInventoryCsv(dashboard.token, reason);

  const exportCatalogCsv = (filters: Parameters<typeof inventoryService.fetchDevices>[2], reason: string) => {
    if (!dashboard.selectedStoreId) {
      throw new Error("Selecciona una sucursal para exportar el catálogo");
    }
    return inventoryService.exportCatalogCsv(
      dashboard.token,
      dashboard.selectedStoreId,
      filters,
      reason,
    );
  };

  const importCatalogCsv = async (file: File, reason: string) => {
    if (!dashboard.selectedStoreId) {
      throw new Error("Selecciona una sucursal para importar productos");
    }
    const summary = await inventoryService.importCatalogCsv(
      dashboard.token,
      dashboard.selectedStoreId,
      file,
      reason,
    );
    await dashboard.refreshInventoryAfterTransfer();
    return summary;
  };

  const storeValuationSnapshot = useMemo(() => {
    if (!dashboard.selectedStoreId || !dashboard.selectedStore) {
      return null;
    }
    const summaryEntry = dashboard.summary.find(
      (entry) => entry.store_id === dashboard.selectedStoreId,
    );
    if (!summaryEntry) {
      return null;
    }
    const registeredValue = dashboard.selectedStore.inventory_value ?? 0;
    const calculatedValue = summaryEntry.total_value;
    const difference = calculatedValue - registeredValue;
    const differenceAbs = Math.abs(difference);
    const differencePercent =
      registeredValue === 0 ? null : (difference / registeredValue) * 100;

    return {
      storeId: dashboard.selectedStoreId,
      storeName: dashboard.selectedStore.name,
      registeredValue,
      calculatedValue,
      difference,
      differenceAbs,
      differencePercent,
      hasRelevantDifference: differenceAbs >= 1,
    };
  }, [dashboard.selectedStore, dashboard.selectedStoreId, dashboard.summary]);

  const stockByCategory = useMemo(() => {
    if (!dashboard.metrics) {
      return [] as Array<{ label: string; value: number }>;
    }
    return dashboard.metrics.stock_breakdown.map((entry) => ({
      label: entry.label,
      value: entry.value,
    }));
  }, [dashboard.metrics]);

  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 60000); // Update every minute
    return () => clearInterval(interval);
  }, []);

  const expiringReservations = useMemo(() => {
    const threshold = 30 * 60 * 1000; // 30 minutos
    return reservations.filter((reservation) => {
      if (reservation.status !== "RESERVADO") {
        return false;
      }
      const expiresAt = Date.parse(reservation.expires_at);
      return expiresAt - now <= threshold && expiresAt > now;
    });
  }, [reservations, now]);

  // Download wrappers (could be moved to useInventoryReports but kept here for now)
  const downloadInventoryCurrentCsv = (reason: string, filters: InventoryCurrentFilters = {}) =>
    inventoryService.downloadInventoryCurrentCsv(dashboard.token, reason, filters);

  const downloadInventoryCurrentPdf = (reason: string, filters: InventoryCurrentFilters = {}) =>
    inventoryService.downloadInventoryCurrentPdf(dashboard.token, reason, filters);

  const downloadInventoryCurrentXlsx = (reason: string, filters: InventoryCurrentFilters = {}) =>
    inventoryService.downloadInventoryCurrentXlsx(dashboard.token, reason, filters);

  const downloadInventoryValueCsv = (reason: string, filters: InventoryValueFilters = {}) =>
    inventoryService.downloadInventoryValueCsv(dashboard.token, reason, filters);

  const downloadInventoryValuePdf = (reason: string, filters: InventoryValueFilters = {}) =>
    inventoryService.downloadInventoryValuePdf(dashboard.token, reason, filters);

  const downloadInventoryValueXlsx = (reason: string, filters: InventoryValueFilters = {}) =>
    inventoryService.downloadInventoryValueXlsx(dashboard.token, reason, filters);

  const downloadInventoryMovementsCsv = (reason: string, filters: InventoryMovementsFilters = {}) =>
    inventoryService.downloadInventoryMovementsCsv(dashboard.token, reason, filters);

  const downloadInventoryMovementsPdf = (reason: string, filters: InventoryMovementsFilters = {}) =>
    inventoryService.downloadInventoryMovementsPdf(dashboard.token, reason, filters);

  const downloadInventoryMovementsXlsx = (reason: string, filters: InventoryMovementsFilters = {}) =>
    inventoryService.downloadInventoryMovementsXlsx(dashboard.token, reason, filters);

  const downloadTopProductsCsv = (reason: string, filters: InventoryTopProductsFilters = {}) =>
    inventoryService.downloadTopProductsCsv(dashboard.token, reason, filters);

  const downloadTopProductsPdf = (reason: string, filters: InventoryTopProductsFilters = {}) =>
    inventoryService.downloadTopProductsPdf(dashboard.token, reason, filters);

  const downloadTopProductsXlsx = (reason: string, filters: InventoryTopProductsFilters = {}) =>
    inventoryService.downloadTopProductsXlsx(dashboard.token, reason, filters);

  const smartImportInventory = (
    file: File,
    reason: string,
    options: Parameters<typeof inventoryService.smartImportInventory>[3] = {},
  ) => inventoryService.smartImportInventory(dashboard.token, file, reason, options);

  // Adapter for fetchSmartImportHistory to match old signature (returns promise)
  const fetchSmartImportHistoryAdapter = async (_limit = 10) => {
    const res = await fetchSmartImportHistory();
    return res.data || [];
  };

  // Adapter for fetchIncompleteDevices to match old signature
  const fetchIncompleteDevicesAdapter = async (_storeId?: number, _limit = 100) => {
    // Note: The hook is bound to selectedStoreId, so storeId arg might be ignored if different
    // Ideally we should update the hook to accept dynamic storeId or update the caller
    const res = await fetchIncompleteDevices();
    return res.data || [];
  };

  // Adapter for refreshReservations to match old signature (accepts page)
  const refreshReservationsAdapter = async (page = 1) => {
    setReservationsPage(page);
    await refreshReservations();
  };

  return {
    token: dashboard.token,
    enableCatalogPro: dashboard.enableCatalogPro,
    enableVariants: dashboard.enableVariants,
    enableBundles: dashboard.enableBundles,
    stores: dashboard.stores,
    selectedStoreId: dashboard.selectedStoreId,
    setSelectedStoreId: dashboard.setSelectedStoreId,
    selectedStore: dashboard.selectedStore,
    devices: dashboard.devices,
    loading: dashboard.loading,
    totalDevices: dashboard.totalDevices,
    totalItems: dashboard.totalItems,
    totalValue: dashboard.totalValue,
    formatCurrency: dashboard.formatCurrency,
    topStores: dashboard.topStores,
    lowStockDevices: dashboard.lowStockDevices,
    handleMovement: dashboard.handleMovement,
    handleDeviceUpdate: dashboard.handleDeviceUpdate,
    backupHistory: dashboard.backupHistory,
    updateStatus: dashboard.updateStatus,
    lastInventoryRefresh: dashboard.lastInventoryRefresh,
    downloadInventoryReport,
    downloadInventoryCsv,
    exportCatalogCsv,
    importCatalogCsv,
    supplierBatchOverview,
    supplierBatchLoading,
    refreshSupplierBatchOverview,
    stockByCategory,
    recentMovements,
    recentMovementsLoading,
    refreshRecentMovements,
    lowStockThreshold: dashboard.currentLowStockThreshold,
    updateLowStockThreshold: dashboard.updateLowStockThreshold,
    refreshSummary: dashboard.refreshSummary,
    storeValuationSnapshot,
    fetchInventoryCurrentReport,
    downloadInventoryCurrentCsv,
    downloadInventoryCurrentPdf,
    downloadInventoryCurrentXlsx,
    fetchInventoryValueReport,
    fetchInactiveProductsReport,
    fetchInventoryMovementsReport,
    fetchTopProductsReport,
    fetchSyncDiscrepancyReport,
    downloadInventoryValueCsv,
    downloadInventoryValuePdf,
    downloadInventoryValueXlsx,
    downloadInventoryMovementsCsv,
    downloadInventoryMovementsPdf,
    downloadInventoryMovementsXlsx,
    downloadTopProductsCsv,
    downloadTopProductsPdf,
    downloadTopProductsXlsx,
    smartImportInventory,
    fetchSmartImportHistory: fetchSmartImportHistoryAdapter,
    fetchIncompleteDevices: fetchIncompleteDevicesAdapter,
    reservations,
    reservationsMeta,
    reservationsLoading,
    reservationsIncludeExpired,
    setReservationsIncludeExpired,
    refreshReservations: refreshReservationsAdapter,
    createReservation,
    renewReservation,
    cancelReservation,
    expiringReservations,
  };
}
