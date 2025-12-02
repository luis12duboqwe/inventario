import { useState, useEffect, useCallback } from "react";

export function useInventoryAlerts(
  lowStockThreshold: number,
  selectedStoreId: number | null,
  updateLowStockThreshold: (storeId: number, threshold: number, setError: (msg: string | null) => void) => Promise<void>,
  pushToast: (options: { message: string; variant: "success" | "error" | "info" }) => void,
  setError: (message: string | null) => void
) {
  const [thresholdDraft, setThresholdDraft] = useState(lowStockThreshold);
  const [isSavingThreshold, setIsSavingThreshold] = useState(false);

  useEffect(() => {
    setThresholdDraft(lowStockThreshold);
  }, [lowStockThreshold]);

  const updateThresholdDraftValue = useCallback((value: number) => {
    if (Number.isNaN(value)) {
      return;
    }
    const clamped = Math.max(0, Math.min(100, value));
    setThresholdDraft(clamped);
  }, []);

  const handleSaveThreshold = useCallback(async () => {
    if (!selectedStoreId) {
      const message = "Selecciona una sucursal para ajustar el umbral de alertas.";
      setError(message);
      pushToast({ message, variant: "error" });
      return;
    }
    setIsSavingThreshold(true);
    try {
      await updateLowStockThreshold(selectedStoreId, thresholdDraft, setError);
      pushToast({ message: "Umbral de stock bajo actualizado", variant: "success" });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "No fue posible guardar el nuevo umbral.";
      setError(message);
      pushToast({ message, variant: "error" });
      setThresholdDraft(lowStockThreshold);
    } finally {
      setIsSavingThreshold(false);
    }
  }, [
    lowStockThreshold,
    pushToast,
    selectedStoreId,
    setError,
    thresholdDraft,
    updateLowStockThreshold,
  ]);

  return {
    thresholdDraft,
    setThresholdDraft,
    updateThresholdDraftValue,
    handleSaveThreshold,
    isSavingThreshold,
  };
}
