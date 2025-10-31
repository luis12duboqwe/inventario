import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type {
  Device,
  InventoryImportHistoryEntry,
  InventorySmartImportPreview,
  InventorySmartImportResponse,
  InventorySmartImportResult,
  Store,
} from "../../../../api";
import type { ToastMessage } from "../../../dashboard/context/DashboardContext";
import { promptCorporateReason } from "../../../../utils/corporateReason";

export type SmartImportManagerDeps = {
  smartImportInventory: (
    file: File,
    reason: string,
    options?: { commit?: boolean; overrides?: Record<string, string> },
  ) => Promise<InventorySmartImportResponse>;
  fetchSmartImportHistory: (limit?: number) => Promise<InventoryImportHistoryEntry[]>;
  fetchIncompleteDevices: (storeId?: number, limit?: number) => Promise<Device[]>;
  refreshSummary: () => Promise<void> | void;
  selectedStore: Store | null;
  selectedStoreId: number | null;
  pushToast: (toast: Omit<ToastMessage, "id">) => void;
  setError: (message: string | null) => void;
};

export function useSmartImportManager({
  smartImportInventory,
  fetchSmartImportHistory,
  fetchIncompleteDevices,
  refreshSummary,
  selectedStore,
  selectedStoreId,
  pushToast,
  setError,
}: SmartImportManagerDeps) {
  const [smartImportFile, setSmartImportFile] = useState<File | null>(null);
  const [smartImportPreviewState, setSmartImportPreviewState] =
    useState<InventorySmartImportPreview | null>(null);
  const [smartImportResult, setSmartImportResult] = useState<InventorySmartImportResult | null>(null);
  const [smartImportReason, setSmartImportReason] = useState<string | null>(null);
  const [smartImportOverrides, setSmartImportOverrides] = useState<Record<string, string>>({});
  const [smartImportLoading, setSmartImportLoading] = useState(false);
  const [smartImportHistory, setSmartImportHistory] = useState<InventoryImportHistoryEntry[]>([]);
  const [smartImportHistoryLoading, setSmartImportHistoryLoading] = useState(false);
  const [pendingDevices, setPendingDevices] = useState<Device[]>([]);
  const [pendingDevicesLoading, setPendingDevicesLoading] = useState(false);
  const [smartPreviewDirty, setSmartPreviewDirty] = useState(false);
  const smartFileInputRef = useRef<HTMLInputElement | null>(null);

  const ensureSmartReason = useCallback((): string | null => {
    const defaultReason = selectedStore
      ? `Importación inteligente ${selectedStore.name}`
      : "Importación inteligente de inventario";
    if (smartImportReason && smartImportReason.length >= 5) {
      return smartImportReason;
    }
    const reason = promptCorporateReason(defaultReason);
    if (reason === null) {
      pushToast({ message: "Acción cancelada: se requiere motivo corporativo.", variant: "info" });
      return null;
    }
    const normalized = reason.trim();
    if (normalized.length < 5) {
      const message = "Ingresa un motivo corporativo de al menos 5 caracteres.";
      setError(message);
      pushToast({ message, variant: "error" });
      return null;
    }
    setSmartImportReason(normalized);
    return normalized;
  }, [pushToast, selectedStore, setError, smartImportReason]);

  const refreshSmartImportHistory = useCallback(async () => {
    try {
      setSmartImportHistoryLoading(true);
      const history = await fetchSmartImportHistory(10);
      setSmartImportHistory(history);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible obtener el historial de importaciones inteligentes.";
      setError(message);
      pushToast({ message, variant: "error" });
    } finally {
      setSmartImportHistoryLoading(false);
    }
  }, [fetchSmartImportHistory, pushToast, setError]);

  const refreshPendingDevices = useCallback(async () => {
    try {
      setPendingDevicesLoading(true);
      const devicesResponse = await fetchIncompleteDevices(selectedStoreId ?? undefined, 200);
      setPendingDevices(devicesResponse);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible obtener los dispositivos con información pendiente.";
      setError(message);
      pushToast({ message, variant: "error" });
    } finally {
      setPendingDevicesLoading(false);
    }
  }, [fetchIncompleteDevices, pushToast, selectedStoreId, setError]);

  useEffect(() => {
    void refreshSmartImportHistory();
  }, [refreshSmartImportHistory]);

  const handleSmartOverrideChange = useCallback((field: string, header: string) => {
    setSmartImportOverrides((current) => {
      const next = { ...current };
      if (!header) {
        delete next[field];
      } else {
        next[field] = header;
      }
      return next;
    });
    setSmartPreviewDirty(true);
  }, []);

  const handleSmartPreview = useCallback(async () => {
    if (!smartImportFile) {
      const message = "Selecciona un archivo Excel o CSV antes de analizar.";
      setError(message);
      pushToast({ message, variant: "error" });
      return;
    }
    const reason = ensureSmartReason();
    if (!reason) {
      return;
    }
    setSmartImportLoading(true);
    try {
      const response = await smartImportInventory(smartImportFile, reason, {
        commit: false,
        overrides: smartImportOverrides,
      });
      setSmartImportPreviewState(response.preview);
      setSmartImportResult(response.resultado ?? null);
      setSmartPreviewDirty(false);
      if (response.preview.advertencias.length > 0) {
        pushToast({ message: "Análisis completado con advertencias.", variant: "warning" });
      } else {
        pushToast({ message: "Análisis completado correctamente.", variant: "success" });
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "No fue posible analizar el archivo de inventario.";
      setError(message);
      pushToast({ message, variant: "error" });
    } finally {
      setSmartImportLoading(false);
    }
  }, [
    ensureSmartReason,
    pushToast,
    setError,
    smartImportFile,
    smartImportInventory,
    smartImportOverrides,
  ]);

  const handleSmartCommit = useCallback(async () => {
    if (!smartImportFile) {
      const message = "Selecciona un archivo antes de importar.";
      setError(message);
      pushToast({ message, variant: "error" });
      return;
    }
    const reason = ensureSmartReason();
    if (!reason) {
      return;
    }
    setSmartImportLoading(true);
    try {
      const response = await smartImportInventory(smartImportFile, reason, {
        commit: true,
        overrides: smartImportOverrides,
      });
      setSmartImportPreviewState(response.preview);
      setSmartImportResult(response.resultado ?? null);
      setSmartPreviewDirty(false);
      setSmartImportFile(null);
      if (smartFileInputRef.current) {
        smartFileInputRef.current.value = "";
      }
      pushToast({ message: "Importación inteligente completada.", variant: "success" });
      await refreshSmartImportHistory();
      await refreshPendingDevices();
      void refreshSummary();
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible completar la importación inteligente.";
      setError(message);
      pushToast({ message, variant: "error" });
    } finally {
      setSmartImportLoading(false);
    }
  }, [
    ensureSmartReason,
    pushToast,
    refreshPendingDevices,
    refreshSmartImportHistory,
    refreshSummary,
    setError,
    smartImportFile,
    smartImportInventory,
    smartImportOverrides,
  ]);

  const smartImportHeaders = useMemo(() => {
    if (!smartImportPreviewState) {
      return [] as string[];
    }
    const headers = new Set<string>();
    smartImportPreviewState.columnas.forEach((match) => {
      if (match.encabezado_origen) {
        headers.add(match.encabezado_origen);
      }
    });
    return Array.from(headers).sort((a, b) => a.localeCompare(b));
  }, [smartImportPreviewState]);

  const resetSmartImportContext = useCallback(() => {
    setSmartImportPreviewState(null);
    setSmartImportResult(null);
    setSmartImportOverrides({});
    setSmartPreviewDirty(false);
  }, []);

  return {
    smartImportFile,
    setSmartImportFile,
    smartImportPreviewState,
    smartImportResult,
    smartImportOverrides,
    smartImportHeaders,
    smartImportLoading,
    smartImportHistory,
    smartImportHistoryLoading,
    refreshSmartImportHistory,
    pendingDevices,
    pendingDevicesLoading,
    refreshPendingDevices,
    smartPreviewDirty,
    setSmartPreviewDirty,
    smartFileInputRef,
    handleSmartOverrideChange,
    handleSmartPreview,
    handleSmartCommit,
    resetSmartImportContext,
  };
}
