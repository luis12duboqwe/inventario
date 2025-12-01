import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import type { RecurringOrder, RecurringOrderPayload } from "../../../../../api/operations";
import {
  createRecurringOrder,
  executeRecurringOrder,
  listRecurringOrders,
} from "../../../../../api/operations";
import type { PurchaseForm } from "../../../../../types/purchases";

type UsePurchaseTemplatesParams = {
  token: string;
  form: PurchaseForm;
  setForm: React.Dispatch<React.SetStateAction<PurchaseForm>>;
  refreshOrders: (storeId?: number | null) => Promise<void>;
  askReason: (prompt: string) => string | null;
  setError: (msg: string | null) => void;
  setMessage: (msg: string | null) => void;
  onInventoryRefresh?: () => void;
};

export function usePurchaseTemplates(params: UsePurchaseTemplatesParams) {
  const {
    token,
    form,
    setForm,
    refreshOrders,
    askReason,
    setError,
    setMessage,
    onInventoryRefresh,
  } = params;

  const [recurringOrders, setRecurringOrders] = useState<RecurringOrder[]>([]);
  const [recurringLoading, setRecurringLoading] = useState(false);
  const [templateName, setTemplateName] = useState("");
  const [templateDescription, setTemplateDescription] = useState("");
  const [templateSaving, setTemplateSaving] = useState(false);

  const loadRecurringOrders = useCallback(async () => {
    try {
      setRecurringLoading(true);
      const data = await listRecurringOrders(token, "purchase");
      setRecurringOrders(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible cargar las plantillas de compras");
    } finally {
      setRecurringLoading(false);
    }
  }, [token, setError]);

  useEffect(() => {
    void loadRecurringOrders();
  }, [loadRecurringOrders]);

  const handleSaveTemplate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form.storeId || !form.deviceId) {
      setError("Selecciona sucursal y dispositivo antes de guardar la plantilla.");
      return;
    }
    if (!form.supplier.trim()) {
      setError("Indica un proveedor válido antes de guardar la plantilla.");
      return;
    }
    const normalizedName = templateName.trim();
    if (normalizedName.length < 3) {
      setError("El nombre de la plantilla debe tener al menos 3 caracteres.");
      return;
    }
    const reason = askReason("Motivo corporativo para guardar la plantilla");
    if (!reason) {
      return;
    }
    const normalizedDescription = templateDescription.trim();
    const templatePayload: Record<string, unknown> = {
      store_id: form.storeId,
      supplier: form.supplier.trim(),
      items: [
        {
          device_id: form.deviceId,
          quantity_ordered: Math.max(1, form.quantity),
          unit_cost: Math.max(0, form.unitCost),
        },
      ],
    };
    if (normalizedDescription) {
      templatePayload.notes = normalizedDescription;
    }

    const payload: RecurringOrderPayload = {
      name: normalizedName,
      order_type: "purchase",
      payload: templatePayload,
    };
    if (normalizedDescription) {
      payload.description = normalizedDescription;
    }
    try {
      setError(null);
      setTemplateSaving(true);
      await createRecurringOrder(token, payload, reason);
      setMessage("Plantilla de compra guardada correctamente.");
      setTemplateName("");
      setTemplateDescription("");
      await loadRecurringOrders();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible guardar la plantilla");
    } finally {
      setTemplateSaving(false);
    }
  };

  const handleApplyTemplate = (template: RecurringOrder) => {
    const payload = template.payload as Record<string, unknown>;
    const items = Array.isArray(payload?.items) ? (payload.items as Record<string, unknown>[]) : [];
    const firstItem = items[0] ?? {};
    const supplierValue = typeof payload?.supplier === "string" ? (payload.supplier as string) : form.supplier;
    const storeValue = typeof payload?.store_id === "number" ? (payload.store_id as number) : form.storeId;
    setForm({
      storeId: storeValue ?? null,
      supplier: supplierValue,
      deviceId: typeof firstItem.device_id === "number" ? (firstItem.device_id as number) : form.deviceId,
      quantity: typeof firstItem.quantity_ordered === "number" ? (firstItem.quantity_ordered as number) : form.quantity,
      unitCost: typeof firstItem.unit_cost === "number" ? (firstItem.unit_cost as number) : form.unitCost,
    });
    setMessage(`Plantilla "${template.name}" aplicada al formulario.`);
  };

  const handleExecuteTemplate = async (template: RecurringOrder) => {
    const reason = askReason(`Motivo corporativo para ejecutar "${template.name}"`);
    if (!reason) {
      return;
    }
    try {
      setError(null);
      const result = await executeRecurringOrder(token, template.id, reason);
      setMessage(result.summary);
      const targetStore = template.store_id ?? form.storeId;
      if (targetStore) {
        await refreshOrders(targetStore);
      }
      await loadRecurringOrders();
      onInventoryRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible ejecutar la plantilla");
    }
  };

  const getTemplateSupplier = (template: RecurringOrder): string => {
    const payload = template.payload as Record<string, unknown>;
    if (payload && typeof payload.supplier === "string") {
      return payload.supplier as string;
    }
    return template.store_name ?? "Proveedor no especificado";
  };

  return {
    recurringOrders,
    recurringLoading,
    templateName,
    templateDescription,
    templateSaving,
    setTemplateName,
    setTemplateDescription,
    handleSaveTemplate,
    handleApplyTemplate,
    handleExecuteTemplate,
    getTemplateSupplier,
    loadRecurringOrders,
  };
}
