import { useState } from "react";
import type { FormEvent } from "react";
import { importPurchaseOrdersCsv } from "../../../../../api/purchases";
import type { PurchaseForm } from "../../../../../types/purchases";

type UsePurchaseCsvParams = {
  token: string;
  form: PurchaseForm;
  refreshOrders: (storeId?: number | null) => Promise<void>;
  loadRecurringOrders: () => Promise<void>;
  askReason: (prompt: string) => string | null;
  setError: (msg: string | null) => void;
  setMessage: (msg: string | null) => void;
  onInventoryRefresh?: () => void;
};

export function usePurchaseCsv(params: UsePurchaseCsvParams) {
  const {
    token,
    form,
    refreshOrders,
    loadRecurringOrders,
    askReason,
    setError,
    setMessage,
    onInventoryRefresh,
  } = params;

  const [csvLoading, setCsvLoading] = useState(false);

  const handleImportCsv = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const fileInput = event.currentTarget.elements.namedItem("csvFile") as HTMLInputElement | null;
    const file = fileInput?.files?.[0];
    if (!file) {
      setError("Selecciona un archivo CSV corporativo.");
      return;
    }
    const reason = askReason("Motivo corporativo de la importación CSV");
    if (!reason) {
      return;
    }
    try {
      setError(null);
      setCsvLoading(true);
      const response = await importPurchaseOrdersCsv(token, file, reason);
      setMessage(`Importación completada: ${response.imported} orden(es).`);
      if (response.errors.length > 0) {
        setError(response.errors.join(" · "));
      }
      const targetStore = form.storeId ?? response.orders[0]?.store_id ?? null;
      if (targetStore) {
        await refreshOrders(targetStore);
      }
      await loadRecurringOrders();
      onInventoryRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible importar el CSV de compras");
    } finally {
      setCsvLoading(false);
      event.currentTarget.reset();
    }
  };

  return {
    csvLoading,
    handleImportCsv,
  };
}
