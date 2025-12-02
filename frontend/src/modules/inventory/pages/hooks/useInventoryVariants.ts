import { useState, useCallback, useEffect } from "react";
import { inventoryService } from "../../services/inventoryService";
import type { ProductVariant, ProductVariantCreateInput, ProductVariantUpdateInput } from "@api/inventory";

type UseInventoryVariantsProps = {
  token: string;
  selectedStoreId: number | null;
  enableVariants: boolean;
  pushToast: (toast: { message: string; variant: "success" | "error" | "info" | "warning" }) => void;
  setError: (error: string | null) => void;
};

export function useInventoryVariants({
  token,
  selectedStoreId,
  enableVariants,
  pushToast,
  setError,
}: UseInventoryVariantsProps) {
  const [variants, setVariants] = useState<ProductVariant[]>([]);
  const [variantsLoading, setVariantsLoading] = useState(false);
  const [variantsIncludeInactive, setVariantsIncludeInactive] = useState(false);

  const refreshVariants = useCallback(async () => {
    if (!enableVariants) {
      setVariants([]);
      return;
    }
    try {
      setVariantsLoading(true);
      const data = await inventoryService.fetchVariants(token, {
        ...(selectedStoreId ? { storeId: selectedStoreId } : {}),
        includeInactive: variantsIncludeInactive,
      });
      setVariants(data);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible obtener las variantes del inventario.";
      setError(message);
      pushToast({ message, variant: "error" });
    } finally {
      setVariantsLoading(false);
    }
  }, [enableVariants, selectedStoreId, token, pushToast, setError, variantsIncludeInactive]);

  const handleCreateVariant = useCallback(
    async (deviceId: number, payload: ProductVariantCreateInput, reason: string) => {
      if (!enableVariants) {
        return;
      }
      try {
        await inventoryService.createVariant(token, deviceId, payload, reason);
        pushToast({ message: "Variante registrada correctamente.", variant: "success" });
        await refreshVariants();
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "No fue posible registrar la variante.";
        setError(message);
        pushToast({ message, variant: "error" });
      }
    },
    [enableVariants, token, pushToast, refreshVariants, setError],
  );

  const handleUpdateVariant = useCallback(
    async (variantId: number, payload: ProductVariantUpdateInput, reason: string) => {
      if (!enableVariants) {
        return;
      }
      try {
        await inventoryService.updateVariant(token, variantId, payload, reason);
        pushToast({ message: "Variante actualizada.", variant: "success" });
        await refreshVariants();
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "No fue posible actualizar la variante.";
        setError(message);
        pushToast({ message, variant: "error" });
      }
    },
    [enableVariants, token, pushToast, refreshVariants, setError],
  );

  const handleArchiveVariant = useCallback(
    async (variantId: number, reason: string) => {
      if (!enableVariants) {
        return;
      }
      try {
        await inventoryService.archiveVariant(token, variantId, reason);
        pushToast({ message: "Variante archivada.", variant: "success" });
        await refreshVariants();
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "No fue posible archivar la variante.";
        setError(message);
        pushToast({ message, variant: "error" });
      }
    },
    [enableVariants, token, pushToast, refreshVariants, setError],
  );

  useEffect(() => {
    void refreshVariants();
  }, [refreshVariants]);

  return {
    variants,
    variantsLoading,
    variantsIncludeInactive,
    setVariantsIncludeInactive,
    refreshVariants,
    handleCreateVariant,
    handleUpdateVariant,
    handleArchiveVariant,
  };
}
