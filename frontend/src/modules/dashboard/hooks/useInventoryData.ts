import { useState, useCallback, useMemo } from "react";
import {
  downloadInventoryPdf,
  getDevices,
  getInventoryMetrics,
  registerMovement,
  updateDevice,
} from "@api/inventory";
import { getStores, getSummary } from "@api/stores";
import { safeArray } from "../../../utils/safeValues";
import type {
  Device,
  DeviceUpdateInput,
  InventoryMetrics,
  MovementInput,
  Store,
} from "@api/inventory";
import type { Summary } from "@api/stores";
import type { ToastMessage } from "../hooks/useUIState";
import type { LocalSyncEventInput, LocalSyncQueueItem } from "../../sync/services/syncClient";

const DEFAULT_LOW_STOCK_THRESHOLD = 5;

export function useInventoryData(
  token: string,
  pushToast: (toast: Omit<ToastMessage, "id">) => void,
  friendlyErrorMessage: (msg: string) => string,
  syncClient: { enqueue: (item: LocalSyncEventInput) => Promise<LocalSyncQueueItem> }
) {
  const [stores, setStores] = useState<Store[]>([]);
  const [summary, setSummary] = useState<Summary[]>([]);
  const [metrics, setMetrics] = useState<InventoryMetrics | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [lastInventoryRefresh, setLastInventoryRefresh] = useState<Date | null>(null);
  const [selectedStoreId, setSelectedStoreId] = useState<number | null>(null);
  const [lowStockThresholds, setLowStockThresholds] = useState<Record<number, number>>({});

  const getThresholdForStore = useCallback(
    (storeId: number | null | undefined) => {
      if (!storeId) {
        return DEFAULT_LOW_STOCK_THRESHOLD;
      }
      return lowStockThresholds[storeId] ?? DEFAULT_LOW_STOCK_THRESHOLD;
    },
    [lowStockThresholds]
  );

  const selectedStore = useMemo(
    () => stores.find((store) => store.id === selectedStoreId) ?? null,
    [stores, selectedStoreId]
  );

  const currentLowStockThreshold = useMemo(
    () => getThresholdForStore(selectedStoreId),
    [getThresholdForStore, selectedStoreId]
  );

  const refreshSummary = useCallback(async () => {
    const threshold = getThresholdForStore(selectedStoreId);
    const [summaryRaw, metricsData] = await Promise.all([
      getSummary(token),
      getInventoryMetrics(token, threshold),
    ]);
    setSummary(safeArray(summaryRaw));
    setMetrics(metricsData);
  }, [getThresholdForStore, selectedStoreId, token]);

  const refreshStores = useCallback(async () => {
    try {
      const storesRaw = await getStores(token);
      setStores(safeArray(storesRaw));
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible actualizar las sucursales";
      const friendly = friendlyErrorMessage(message);
      pushToast({ message: friendly, variant: "error" });
    }
  }, [friendlyErrorMessage, pushToast, token]);

  const fetchInventoryData = useCallback(async () => {
    try {
      const [storesRaw, summaryRaw, metricsData] = await Promise.all([
        getStores(token),
        getSummary(token),
        getInventoryMetrics(token),
      ]);
      const storesData = safeArray(storesRaw);
      const summaryData = safeArray(summaryRaw);
      setStores(storesData);
      setLowStockThresholds((current) => {
        const next = { ...current };
        for (const store of storesData) {
          if (next[store.id] === undefined) {
            next[store.id] = DEFAULT_LOW_STOCK_THRESHOLD;
          }
        }
        return next;
      });
      setSummary(summaryData);
      setMetrics(metricsData);

      const firstStore = storesData[0];
      if (firstStore) {
        setSelectedStoreId(firstStore.id);
        const devicesData = await getDevices(token, firstStore.id);
        setDevices(safeArray(devicesData));
        setLastInventoryRefresh(new Date());
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible cargar los datos de inventario";
      const friendly = friendlyErrorMessage(message);
      pushToast({ message: friendly, variant: "error" });
      throw err;
    }
  }, [token, pushToast, friendlyErrorMessage]);

  const handleMovement = useCallback(
    async (payload: MovementInput, setError: (msg: string | null) => void, setMessage: (msg: string | null) => void) => {
      if (!selectedStoreId) {
        return;
      }
      const comment = payload.comentario.trim();
      if (comment.length < 5) {
        setError("Indica un motivo corporativo de al menos 5 caracteres.");
        return;
      }
      try {
        setError(null);
        await registerMovement(token, selectedStoreId, payload, comment);
        setMessage("Movimiento registrado correctamente");
        pushToast({ message: "Movimiento registrado", variant: "success" });
        await Promise.all([
          refreshSummary(),
          getDevices(token, selectedStoreId).then((items) => setDevices(safeArray(items))),
        ]);
        setLastInventoryRefresh(new Date());
      } catch (err) {
        const message = err instanceof Error ? err.message : "No se pudo registrar el movimiento";
        const friendly = friendlyErrorMessage(message);
        setError(friendly);
        pushToast({ message: friendly, variant: "error" });
        if (typeof navigator === "undefined" || !navigator.onLine) {
          try {
            await syncClient.enqueue({
              eventType: "inventory.movement",
              payload: {
                store_id: selectedStoreId,
                movement: payload,
              },
              idempotencyKey: `inventory-movement-${selectedStoreId}-${Date.now()}`,
            });
            pushToast({ message: "Movimiento guardado en cola local.", variant: "info" });
          } catch (syncError) {
            console.warn("No fue posible guardar el movimiento en la cola local", syncError);
          }
        }
      }
    },
    [friendlyErrorMessage, pushToast, refreshSummary, selectedStoreId, token, syncClient]
  );

  const handleDeviceUpdate = useCallback(
    async (deviceId: number, updates: DeviceUpdateInput, reason: string, setError: (msg: string | null) => void, setMessage: (msg: string | null) => void) => {
      if (!selectedStoreId) {
        return;
      }
      const normalizedReason = reason.trim();
      if (normalizedReason.length < 5) {
        setError("Indica un motivo corporativo de al menos 5 caracteres.");
        return;
      }
      if (Object.keys(updates).length === 0) {
        setError("No hay cambios por aplicar en el dispositivo seleccionado.");
        return;
      }
      try {
        setError(null);
        await updateDevice(token, selectedStoreId, deviceId, updates, normalizedReason);
        setMessage("Dispositivo actualizado correctamente");
        pushToast({ message: "Ficha de dispositivo actualizada", variant: "success" });
        await Promise.all([
          refreshSummary(),
          getDevices(token, selectedStoreId).then((items) => setDevices(safeArray(items))),
        ]);
        setLastInventoryRefresh(new Date());
      } catch (err) {
        const message = err instanceof Error ? err.message : "No se pudo actualizar el dispositivo";
        const friendly = friendlyErrorMessage(message);
        setError(friendly);
        pushToast({ message: friendly, variant: "error" });
        throw new Error(friendly);
      }
    },
    [friendlyErrorMessage, pushToast, refreshSummary, selectedStoreId, token]
  );

  const refreshInventoryAfterTransfer = useCallback(async () => {
    await refreshSummary();
    if (selectedStoreId) {
      const devicesData = await getDevices(token, selectedStoreId);
      setDevices(safeArray(devicesData));
      setLastInventoryRefresh(new Date());
    }
  }, [refreshSummary, selectedStoreId, token]);

  const updateLowStockThreshold = useCallback(
    async (storeId: number, threshold: number, setError: (msg: string | null) => void) => {
      const previous = getThresholdForStore(storeId);
      setLowStockThresholds((current) => ({ ...current, [storeId]: threshold }));
      if (selectedStoreId !== storeId) {
        return;
      }
      try {
        const metricsData = await getInventoryMetrics(token, threshold);
        setMetrics(metricsData);
      } catch (err) {
        setLowStockThresholds((current) => ({ ...current, [storeId]: previous }));
        const message = err instanceof Error ? err.message : "No fue posible actualizar el umbral de stock bajo";
        const friendly = friendlyErrorMessage(message);
        setError(friendly);
        pushToast({ message: friendly, variant: "error" });
        throw new Error(friendly);
      }
    },
    [friendlyErrorMessage, getThresholdForStore, pushToast, selectedStoreId, token]
  );

  const downloadInventoryReport = useCallback(
    async (reason: string) => {
      await downloadInventoryPdf(token, reason);
    },
    [token]
  );

  const totals = useMemo(() => {
    const totalDevices = metrics?.totals.devices ?? summary.reduce((acc, store) => acc + store.devices.length, 0);
    const totalItems = metrics?.totals.total_units ?? summary.reduce((acc, store) => acc + store.total_items, 0);
    const totalValue = metrics?.totals.total_value ?? summary.reduce(
      (acc, store) => acc + store.devices.reduce((deviceAcc: number, device: Device) => deviceAcc + device.inventory_value, 0),
      0
    );

    const lowStock = (metrics?.low_stock_devices ?? []).filter((entry) => {
      if (!selectedStoreId) {
        return true;
      }
      return entry.store_id === selectedStoreId;
    });
    const topStores = metrics?.top_stores ?? [];

    return { totalDevices, totalItems, totalValue, lowStock, topStores };
  }, [metrics, selectedStoreId, summary]);

  return {
    stores,
    setStores,
    summary,
    metrics,
    setMetrics,
    devices,
    setDevices,
    lastInventoryRefresh,
    setLastInventoryRefresh,
    selectedStoreId,
    setSelectedStoreId,
    selectedStore,
    currentLowStockThreshold,
    refreshSummary,
    refreshStores,
    fetchInventoryData,
    handleMovement,
    handleDeviceUpdate,
    refreshInventoryAfterTransfer,
    updateLowStockThreshold,
    downloadInventoryReport,
    totals,
    getThresholdForStore,
  };
}
