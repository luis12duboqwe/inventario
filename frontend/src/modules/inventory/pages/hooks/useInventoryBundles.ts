import { useState, useCallback, useEffect } from "react";
import { inventoryService } from "../../services/inventoryService";
import type { ProductBundle, ProductBundleCreateInput, ProductBundleUpdateInput } from "@api/inventory";

type UseInventoryBundlesProps = {
  token: string;
  selectedStoreId: number | null;
  enableBundles: boolean;
  pushToast: (toast: { message: string; variant: "success" | "error" | "info" | "warning" }) => void;
  setError: (error: string | null) => void;
};

export function useInventoryBundles({
  token,
  selectedStoreId,
  enableBundles,
  pushToast,
  setError,
}: UseInventoryBundlesProps) {
  const [bundles, setBundles] = useState<ProductBundle[]>([]);
  const [bundlesLoading, setBundlesLoading] = useState(false);
  const [bundlesIncludeInactive, setBundlesIncludeInactive] = useState(false);

  const refreshBundles = useCallback(async () => {
    if (!enableBundles) {
      setBundles([]);
      return;
    }
    try {
      setBundlesLoading(true);
      const data = await inventoryService.fetchBundles(token, {
        ...(selectedStoreId ? { storeId: selectedStoreId } : {}),
        includeInactive: bundlesIncludeInactive,
      });
      setBundles(data);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "No fue posible obtener los combos configurados.";
      setError(message);
      pushToast({ message, variant: "error" });
    } finally {
      setBundlesLoading(false);
    }
  }, [enableBundles, selectedStoreId, token, bundlesIncludeInactive, pushToast, setError]);

  const handleCreateBundle = useCallback(
    async (payload: ProductBundleCreateInput, reason: string) => {
      if (!enableBundles) {
        return;
      }
      const resolvedStoreId = payload.store_id ?? selectedStoreId ?? undefined;
      const bundlePayload =
        resolvedStoreId !== undefined ? { ...payload, store_id: resolvedStoreId } : payload;
      try {
        await inventoryService.createBundle(token, bundlePayload, reason);
        pushToast({ message: "Combo creado correctamente.", variant: "success" });
        await refreshBundles();
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "No fue posible registrar el combo.";
        setError(message);
        pushToast({ message, variant: "error" });
      }
    },
    [enableBundles, selectedStoreId, token, pushToast, refreshBundles, setError],
  );

  const handleUpdateBundle = useCallback(
    async (bundleId: number, payload: ProductBundleUpdateInput, reason: string) => {
      if (!enableBundles) {
        return;
      }
      try {
        await inventoryService.updateBundle(token, bundleId, payload, reason);
        pushToast({ message: "Combo actualizado.", variant: "success" });
        await refreshBundles();
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "No fue posible actualizar el combo.";
        setError(message);
        pushToast({ message, variant: "error" });
      }
    },
    [enableBundles, token, pushToast, refreshBundles, setError],
  );

  const handleArchiveBundle = useCallback(
    async (bundleId: number, reason: string) => {
      if (!enableBundles) {
        return;
      }
      try {
        await inventoryService.archiveBundle(token, bundleId, reason);
        pushToast({ message: "Combo archivado.", variant: "success" });
        await refreshBundles();
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "No fue posible archivar el combo.";
        setError(message);
        pushToast({ message, variant: "error" });
      }
    },
    [enableBundles, token, pushToast, refreshBundles, setError],
  );

  useEffect(() => {
    void refreshBundles();
  }, [refreshBundles]);

  return {
    bundles,
    bundlesLoading,
    bundlesIncludeInactive,
    setBundlesIncludeInactive,
    refreshBundles,
    handleCreateBundle,
    handleUpdateBundle,
    handleArchiveBundle,
  };
}
