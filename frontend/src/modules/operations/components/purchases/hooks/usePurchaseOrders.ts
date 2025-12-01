import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import {
  cancelPurchaseOrder,
  createPurchaseOrder,
  listPurchaseOrders,
  receivePurchaseOrder,
  registerPurchaseReturn,
} from "../../../../../api/purchases";
import type { PurchaseOrder, PurchaseReceiveInput, PurchaseReturnInput } from "../../../../../api/purchases";
import type { PurchaseForm } from "../../../../../types/purchases";
import type { Device } from "../../../../../api/inventory";
import { getDevices } from "../../../../../api/inventory";

type UsePurchaseOrdersParams = {
  token: string;
  defaultStoreId: number | null;
  askReason: (prompt: string) => string | null;
  setError: (msg: string | null) => void;
  setMessage: (msg: string | null) => void;
  onInventoryRefresh?: () => void;
};

const initialForm: PurchaseForm = {
  storeId: null,
  supplier: "",
  deviceId: null,
  quantity: 1,
  unitCost: 0,
};

export function usePurchaseOrders(params: UsePurchaseOrdersParams) {
  const { token, defaultStoreId, askReason, setError, setMessage, onInventoryRefresh } = params;
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState<PurchaseForm>({ ...initialForm, storeId: defaultStoreId });
  const [devices, setDevices] = useState<Device[]>([]);

  const refreshOrders = useCallback(
    async (storeId?: number | null) => {
      if (!storeId) {
        setOrders([]);
        return;
      }
      try {
        setLoading(true);
        const data = await listPurchaseOrders(token, storeId);
        setOrders(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible cargar las órdenes de compra");
      } finally {
        setLoading(false);
      }
    },
    [token, setError],
  );

  useEffect(() => {
    setForm((current) => ({ ...current, storeId: defaultStoreId ?? null }));
  }, [defaultStoreId]);

  useEffect(() => {
    void refreshOrders(form.storeId ?? undefined);
  }, [form.storeId, refreshOrders]);

  useEffect(() => {
    const loadDevices = async () => {
      if (!form.storeId) {
        setDevices([]);
        return;
      }
      try {
        const data = await getDevices(token, form.storeId);
        setDevices(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible cargar los dispositivos");
      }
    };

    void loadDevices();
  }, [form.storeId, token, setError]);

  const updateForm = (updates: Partial<PurchaseForm>) => {
    setForm((current) => ({ ...current, ...updates }));
  };

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form.storeId || !form.deviceId) {
      setError("Selecciona sucursal y dispositivo.");
      return;
    }
    if (!form.supplier.trim()) {
      setError("Indica un proveedor válido.");
      return;
    }
    const reason = askReason("Motivo corporativo de la compra");
    if (!reason) {
      return;
    }
    try {
      setError(null);
      await createPurchaseOrder(
        token,
        {
          store_id: form.storeId,
          supplier: form.supplier.trim(),
          items: [
            {
              device_id: form.deviceId,
              quantity_ordered: Math.max(1, form.quantity),
              unit_cost: Math.max(0, form.unitCost),
            },
          ],
        },
        reason,
      );
      setMessage("Orden de compra registrada correctamente");
      setForm((current) => ({ ...initialForm, storeId: current.storeId }));
      await refreshOrders(form.storeId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible crear la orden de compra");
    }
  };

  const handleReceive = async (order: PurchaseOrder, recordDevices: Device[]) => {
    const reason = askReason("Motivo de la recepción");
    if (!reason) {
      return;
    }
    const pendingItems = order.items
      .map((item) => ({
        device_id: item.device_id,
        quantity: Math.max(0, item.quantity_ordered - item.quantity_received),
      }))
      .filter((entry) => entry.quantity > 0);

    if (pendingItems.length === 0) {
      setMessage("La orden ya fue recibida por completo.");
      return;
    }
    const itemsWithBatch: PurchaseReceiveInput["items"] = [];
    for (const entry of pendingItems) {
      const deviceInfo =
        recordDevices.find((device) => device.id === entry.device_id) ??
        devices.find((device) => device.id === entry.device_id);
      const promptLabel = deviceInfo
        ? `Lote recibido para ${deviceInfo.sku} · ${deviceInfo.name} (opcional)`
        : `Lote recibido para el dispositivo #${entry.device_id} (opcional)`;
      const batchInput = window.prompt(promptLabel, "");
      if (batchInput === null) {
        setMessage("Recepción cancelada por el usuario.");
        return;
      }
      const normalizedBatch = batchInput.trim();
      if (normalizedBatch) {
        itemsWithBatch.push({ ...entry, batch_code: normalizedBatch });
      } else {
        itemsWithBatch.push(entry);
      }
    }

    try {
      await receivePurchaseOrder(token, order.id, { items: itemsWithBatch }, reason);
      setMessage("Orden actualizada y productos recibidos");
      await refreshOrders(order.store_id);
      onInventoryRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible recibir la orden");
    }
  };

  const handleCancel = async (order: PurchaseOrder) => {
    const reason = askReason("Motivo de cancelación");
    if (!reason) {
      return;
    }
    try {
      await cancelPurchaseOrder(token, order.id, reason);
      setMessage("Orden cancelada");
      await refreshOrders(order.store_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible cancelar la orden");
    }
  };

  const handleReturn = async (order: PurchaseOrder) => {
    const reason = askReason("Motivo de la devolución");
    if (!reason) {
      return;
    }

    const returnableItem = order.items.find(i => i.quantity_received > 0);

    if (!returnableItem) {
      setError("No hay artículos recibidos para devolver en esta orden.");
      return;
    }

    const quantityStr = window.prompt(`Cantidad a devolver (Máx: ${returnableItem.quantity_received})`, "1");
    if (!quantityStr) return;

    const quantity = parseInt(quantityStr, 10);
    if (isNaN(quantity) || quantity <= 0 || quantity > returnableItem.quantity_received) {
      setError("Cantidad inválida.");
      return;
    }

    try {
      const payload: PurchaseReturnInput = {
        device_id: returnableItem.device_id,
        quantity: quantity,
        reason: reason,
        category: "defecto",
        disposition: "defectuoso"
      };

      await registerPurchaseReturn(token, order.id, payload, reason);
      setMessage("Devolución registrada correctamente");
      await refreshOrders(order.store_id);
      onInventoryRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible registrar la devolución");
    }
  };

  return {
    orders,
    loading,
    form,
    devices,
    updateForm,
    handleCreate,
    handleReceive,
    handleCancel,
    handleReturn,
    refreshOrders,
    setForm, // Exposed for templates
  };
}
