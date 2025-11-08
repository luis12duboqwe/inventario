import { useCallback, useEffect, useMemo, useState } from "react";

import type {
  InventoryCurrentFilters,
  InventoryMovementsFilters,
  InventoryTopProductsFilters,
  InventoryValueFilters,
  InventoryReservation,
  InventoryReservationInput,
  InventoryReservationRenewInput,
  MovementReportEntry,
  SupplierBatchOverviewItem,
} from "../../../api";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import { inventoryService } from "../services/inventoryService";

export function useInventoryModule() {
  const dashboard = useDashboard();
  // Desestructurar referencias necesarias para estabilizar dependencias de hooks
  const { token, selectedStoreId, setError, pushToast } = dashboard;
  const RESERVATION_PAGE_SIZE = 20;

  const [supplierBatchOverview, setSupplierBatchOverview] = useState<
    SupplierBatchOverviewItem[]
  >([]);
  const [supplierBatchLoading, setSupplierBatchLoading] = useState(false);
  const [recentMovements, setRecentMovements] = useState<MovementReportEntry[]>([]);
  const [recentMovementsLoading, setRecentMovementsLoading] = useState(false);
  const [reservations, setReservations] = useState<InventoryReservation[]>([]);
  const [reservationsMeta, setReservationsMeta] = useState({
    page: 1,
    size: RESERVATION_PAGE_SIZE,
    total: 0,
    pages: 0,
  });
  const [reservationsLoading, setReservationsLoading] = useState(false);
  const [reservationsIncludeExpired, setReservationsIncludeExpired] = useState(false);

  const refreshSupplierBatchOverview = useCallback(async () => {
    if (!selectedStoreId) {
      setSupplierBatchOverview([]);
      return;
    }
    try {
      setSupplierBatchLoading(true);
      const data = await inventoryService.fetchSupplierBatchOverview(
        token,
        selectedStoreId,
      );
      setSupplierBatchOverview(data);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible consultar los lotes recientes por proveedor.";
      setError(message);
      pushToast({ message, variant: "error" });
    } finally {
      setSupplierBatchLoading(false);
    }
  }, [
    pushToast,
    selectedStoreId,
    setError,
    token,
  ]);

  useEffect(() => {
    void refreshSupplierBatchOverview();
  }, [refreshSupplierBatchOverview]);

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

  const refreshRecentMovements = useCallback(async () => {
    try {
      setRecentMovementsLoading(true);
      const filters: InventoryMovementsFilters = {};
      if (selectedStoreId) {
        filters.storeIds = [selectedStoreId];
      }
      const now = new Date();
      const pastDate = new Date(now);
      pastDate.setDate(now.getDate() - 14);
      filters.dateFrom = pastDate.toISOString();
      filters.dateTo = now.toISOString();
      const report = await inventoryService.fetchInventoryMovementsReport(
        token,
        filters,
      );
      setRecentMovements(report.movimientos.slice(0, 8));
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible consultar los movimientos recientes.";
      setError(message);
      pushToast({ message, variant: "error" });
    } finally {
      setRecentMovementsLoading(false);
    }
  }, [
    pushToast,
    selectedStoreId,
    setError,
    token,
  ]);

  useEffect(() => {
    void refreshRecentMovements();
  }, [refreshRecentMovements, dashboard.lastInventoryRefresh]);

  const refreshReservations = useCallback(
    async (page = 1) => {
      if (!selectedStoreId) {
        setReservations([]);
        setReservationsMeta({
          page: 1,
          size: RESERVATION_PAGE_SIZE,
          total: 0,
          pages: 0,
        });
        return;
      }
      try {
        setReservationsLoading(true);
        const response = await inventoryService.fetchReservations(token, {
          storeId: selectedStoreId,
          page,
          size: RESERVATION_PAGE_SIZE,
          includeExpired: reservationsIncludeExpired,
        });
        setReservations(response.items);
        setReservationsMeta({
          page: response.page,
          size: response.size,
          total: response.total,
          pages: response.pages,
        });
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "No fue posible consultar las reservas de inventario.";
        setError(message);
        pushToast({ message, variant: "error" });
      } finally {
        setReservationsLoading(false);
      }
    },
    [
      pushToast,
      reservationsIncludeExpired,
      selectedStoreId,
      setError,
      token,
    ],
  );

  useEffect(() => {
    void refreshReservations(1);
  }, [refreshReservations]);

  const createReservation = useCallback(
    async (
      input: Omit<InventoryReservationInput, "store_id">,
      reason: string,
    ) => {
      if (!selectedStoreId) {
        throw new Error("Selecciona una sucursal antes de reservar inventario");
      }
      try {
        await inventoryService.createReservation(
          token,
          {
            ...input,
            store_id: selectedStoreId,
          },
          reason,
        );
        pushToast({
          message: "Reserva creada exitosamente.",
          variant: "success",
        });
        await refreshReservations(reservationsMeta.page);
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "No fue posible crear la reserva de inventario.";
        setError(message);
        pushToast({ message, variant: "error" });
        throw error;
      }
    },
    [
      pushToast,
      refreshReservations,
      reservationsMeta.page,
      selectedStoreId,
      setError,
      token,
    ],
  );

  const renewReservation = useCallback(
    async (
      reservationId: number,
      input: InventoryReservationRenewInput,
      reason: string,
    ) => {
      try {
        await inventoryService.renewReservation(
          token,
          reservationId,
          input,
          reason,
        );
        pushToast({
          message: "Reserva renovada correctamente.",
          variant: "success",
        });
        await refreshReservations(reservationsMeta.page);
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "No fue posible renovar la reserva.";
        setError(message);
        pushToast({ message, variant: "error" });
        throw error;
      }
    },
    [
      pushToast,
      refreshReservations,
      reservationsMeta.page,
      setError,
      token,
    ],
  );

  const cancelReservation = useCallback(
    async (reservationId: number, reason: string) => {
      try {
        await inventoryService.cancelReservation(token, reservationId, reason);
        pushToast({
          message: "Reserva cancelada y devuelta al inventario.",
          variant: "success",
        });
        await refreshReservations(reservationsMeta.page);
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "No fue posible cancelar la reserva.";
        setError(message);
        pushToast({ message, variant: "error" });
        throw error;
      }
    },
    [pushToast, refreshReservations, reservationsMeta.page, setError, token],
  );

  const expiringReservations = useMemo(() => {
    const now = Date.now();
    const threshold = 30 * 60 * 1000; // 30 minutos
    return reservations.filter((reservation) => {
      if (reservation.status !== "RESERVADO") {
        return false;
      }
      const expiresAt = Date.parse(reservation.expires_at);
      return expiresAt - now <= threshold && expiresAt > now;
    });
  }, [reservations]);

  const fetchInventoryCurrentReport = useCallback(
    (filters: InventoryCurrentFilters = {}) =>
      inventoryService.fetchInventoryCurrentReport(dashboard.token, filters),
    [dashboard.token],
  );

  const downloadInventoryCurrentCsv = useCallback(
    (reason: string, filters: InventoryCurrentFilters = {}) =>
      inventoryService.downloadInventoryCurrentCsv(dashboard.token, reason, filters),
    [dashboard.token],
  );

  const downloadInventoryCurrentPdf = useCallback(
    (reason: string, filters: InventoryCurrentFilters = {}) =>
      inventoryService.downloadInventoryCurrentPdf(dashboard.token, reason, filters),
    [dashboard.token],
  );

  const downloadInventoryCurrentXlsx = useCallback(
    (reason: string, filters: InventoryCurrentFilters = {}) =>
      inventoryService.downloadInventoryCurrentXlsx(dashboard.token, reason, filters),
    [dashboard.token],
  );

  const fetchInventoryValueReport = useCallback(
    (filters: InventoryValueFilters = {}) =>
      inventoryService.fetchInventoryValueReport(dashboard.token, filters),
    [dashboard.token],
  );

  const fetchInventoryMovementsReport = useCallback(
    (filters: InventoryMovementsFilters = {}) =>
      inventoryService.fetchInventoryMovementsReport(dashboard.token, filters),
    [dashboard.token],
  );

  const fetchTopProductsReport = useCallback(
    (filters: InventoryTopProductsFilters = {}) =>
      inventoryService.fetchTopProductsReport(dashboard.token, filters),
    [dashboard.token],
  );

  const downloadInventoryValueCsv = useCallback(
    (reason: string, filters: InventoryValueFilters = {}) =>
      inventoryService.downloadInventoryValueCsv(dashboard.token, reason, filters),
    [dashboard.token],
  );

  const downloadInventoryValuePdf = useCallback(
    (reason: string, filters: InventoryValueFilters = {}) =>
      inventoryService.downloadInventoryValuePdf(dashboard.token, reason, filters),
    [dashboard.token],
  );

  const downloadInventoryValueXlsx = useCallback(
    (reason: string, filters: InventoryValueFilters = {}) =>
      inventoryService.downloadInventoryValueXlsx(dashboard.token, reason, filters),
    [dashboard.token],
  );

  const downloadInventoryMovementsCsv = useCallback(
    (reason: string, filters: InventoryMovementsFilters = {}) =>
      inventoryService.downloadInventoryMovementsCsv(dashboard.token, reason, filters),
    [dashboard.token],
  );

  const downloadInventoryMovementsPdf = useCallback(
    (reason: string, filters: InventoryMovementsFilters = {}) =>
      inventoryService.downloadInventoryMovementsPdf(dashboard.token, reason, filters),
    [dashboard.token],
  );

  const downloadInventoryMovementsXlsx = useCallback(
    (reason: string, filters: InventoryMovementsFilters = {}) =>
      inventoryService.downloadInventoryMovementsXlsx(dashboard.token, reason, filters),
    [dashboard.token],
  );

  const downloadTopProductsCsv = useCallback(
    (reason: string, filters: InventoryTopProductsFilters = {}) =>
      inventoryService.downloadTopProductsCsv(dashboard.token, reason, filters),
    [dashboard.token],
  );

  const downloadTopProductsPdf = useCallback(
    (reason: string, filters: InventoryTopProductsFilters = {}) =>
      inventoryService.downloadTopProductsPdf(dashboard.token, reason, filters),
    [dashboard.token],
  );

  const downloadTopProductsXlsx = useCallback(
    (reason: string, filters: InventoryTopProductsFilters = {}) =>
      inventoryService.downloadTopProductsXlsx(dashboard.token, reason, filters),
    [dashboard.token],
  );

  const smartImportInventory = useCallback(
    (
      file: File,
      reason: string,
      options: Parameters<typeof inventoryService.smartImportInventory>[3] = {},
    ) => inventoryService.smartImportInventory(dashboard.token, file, reason, options),
    [dashboard.token],
  );

  const fetchSmartImportHistory = useCallback(
    (limit = 10) => inventoryService.fetchSmartImportHistory(dashboard.token, limit),
    [dashboard.token],
  );

  const fetchIncompleteDevices = useCallback(
    (storeId?: number, limit = 100) =>
      inventoryService.fetchIncompleteDevices(dashboard.token, storeId, limit),
    [dashboard.token],
  );

  return {
    token: dashboard.token,
    enableCatalogPro: dashboard.enableCatalogPro,
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
    fetchInventoryMovementsReport,
    fetchTopProductsReport,
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
    fetchSmartImportHistory,
    fetchIncompleteDevices,
    reservations,
    reservationsMeta,
    reservationsLoading,
    reservationsIncludeExpired,
    setReservationsIncludeExpired,
    refreshReservations,
    createReservation,
    renewReservation,
    cancelReservation,
    expiringReservations,
  };
}
