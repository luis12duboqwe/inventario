import { useEffect, useMemo, useState } from "react";
import type { Device, PurchaseOrder, Store } from "../api";
import {
  cancelPurchaseOrder,
  createPurchaseOrder,
  getDevices,
  listPurchaseOrders,
  receivePurchaseOrder,
  registerPurchaseReturn,
} from "../api";

const statusLabels: Record<PurchaseOrder["status"], string> = {
  PENDIENTE: "Pendiente",
  PARCIAL: "Recepción parcial",
  COMPLETADA: "Completada",
  CANCELADA: "Cancelada",
};

type Props = {
  token: string;
  stores: Store[];
  defaultStoreId?: number | null;
  onInventoryRefresh?: () => void;
};

type PurchaseForm = {
  storeId: number | null;
  supplier: string;
  deviceId: number | null;
  quantity: number;
  unitCost: number;
};

const initialForm: PurchaseForm = {
  storeId: null,
  supplier: "",
  deviceId: null,
  quantity: 1,
  unitCost: 0,
};

function Purchases({ token, stores, defaultStoreId = null, onInventoryRefresh }: Props) {
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [form, setForm] = useState<PurchaseForm>({ ...initialForm, storeId: defaultStoreId });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedStore = useMemo(
    () => stores.find((store) => store.id === form.storeId) ?? null,
    [stores, form.storeId]
  );

  const refreshOrders = async (storeId?: number | null) => {
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
  };

  useEffect(() => {
    setForm((current) => ({ ...current, storeId: defaultStoreId ?? null }));
  }, [defaultStoreId]);

  useEffect(() => {
    refreshOrders(form.storeId ?? undefined);
  }, [form.storeId, token]);

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

    loadDevices();
  }, [form.storeId, token]);

  const updateForm = (updates: Partial<PurchaseForm>) => {
    setForm((current) => ({ ...current, ...updates }));
  };

  const handleCreate = async (event: React.FormEvent<HTMLFormElement>) => {
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
        reason
      );
      setMessage("Orden de compra registrada correctamente");
      setForm((current) => ({ ...initialForm, storeId: current.storeId }));
      await refreshOrders(form.storeId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible crear la orden de compra");
    }
  };

  const askReason = (promptText: string) => {
    const reason = window.prompt(promptText, "");
    if (!reason || reason.trim().length < 5) {
      setError("Debes indicar un motivo corporativo (mínimo 5 caracteres).");
      return null;
    }
    return reason.trim();
  };

  const handleReceive = async (order: PurchaseOrder) => {
    const pendingItems = order.items.filter((item) => item.quantity_ordered > item.quantity_received);
    if (pendingItems.length === 0) {
      setMessage("La orden ya fue recibida en su totalidad.");
      return;
    }
    const reason = askReason("Motivo de la recepción");
    if (!reason) {
      return;
    }
    try {
      setError(null);
      const payload = {
        items: pendingItems.map((item) => ({
          device_id: item.device_id,
          quantity: item.quantity_ordered - item.quantity_received,
        })),
      };
      await receivePurchaseOrder(token, order.id, payload, reason);
      setMessage("Recepción aplicada correctamente");
      await refreshOrders(form.storeId);
      onInventoryRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible recibir la orden");
    }
  };

  const handleCancel = async (order: PurchaseOrder) => {
    if (order.status === "COMPLETADA" || order.status === "CANCELADA") {
      setMessage("La orden ya está cerrada.");
      return;
    }
    const reason = askReason("Motivo de cancelación");
    if (!reason) {
      return;
    }
    try {
      setError(null);
      await cancelPurchaseOrder(token, order.id, reason);
      setMessage("Orden cancelada");
      await refreshOrders(form.storeId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible cancelar la orden");
    }
  };

  const handleReturn = async (order: PurchaseOrder) => {
    if (order.items.length === 0) {
      return;
    }
    const deviceId = order.items[0].device_id;
    const quantityRaw = window.prompt("Cantidad a devolver al proveedor", "1");
    const quantity = quantityRaw ? Number(quantityRaw) : NaN;
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setError("Indica una cantidad válida para la devolución.");
      return;
    }
    const reason = askReason("Motivo corporativo de la devolución");
    if (!reason) {
      return;
    }
    try {
      await registerPurchaseReturn(
        token,
        order.id,
        { device_id: deviceId, quantity, reason },
        reason
      );
      setMessage("Devolución al proveedor registrada");
      await refreshOrders(form.storeId);
      onInventoryRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible registrar la devolución");
    }
  };

  return (
    <section className="card">
      <h2>Órdenes de compra</h2>
      <p className="card-subtitle">
        Captura nuevas órdenes, recibe productos parciales y conserva un historial auditado de compras.
      </p>
      {error ? <div className="alert error">{error}</div> : null}
      {message ? <div className="alert success">{message}</div> : null}
      <form className="form-grid" onSubmit={handleCreate}>
        <label>
          Sucursal
          <select
            value={form.storeId ?? ""}
            onChange={(event) => updateForm({ storeId: event.target.value ? Number(event.target.value) : null })}
          >
            <option value="">Selecciona una sucursal</option>
            {stores.map((store) => (
              <option key={store.id} value={store.id}>
                {store.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Proveedor
          <input
            value={form.supplier}
            onChange={(event) => updateForm({ supplier: event.target.value })}
            placeholder="Proveedor corporativo"
          />
        </label>
        <label>
          Dispositivo
          <select
            value={form.deviceId ?? ""}
            onChange={(event) => updateForm({ deviceId: event.target.value ? Number(event.target.value) : null })}
            disabled={!selectedStore}
          >
            <option value="">Selecciona un dispositivo</option>
            {devices.map((device) => (
              <option key={device.id} value={device.id}>
                {device.sku} · {device.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Cantidad ordenada
          <input
            type="number"
            min={1}
            value={form.quantity}
            onChange={(event) => updateForm({ quantity: Number(event.target.value) })}
          />
        </label>
        <label>
          Costo unitario MXN
          <input
            type="number"
            min={0}
            step="0.01"
            value={form.unitCost}
            onChange={(event) => updateForm({ unitCost: Number(event.target.value) })}
          />
        </label>
        <button type="submit" className="btn btn--primary">
          Registrar orden
        </button>
      </form>

      <div className="section-divider">
        <h3>Historial reciente</h3>
        {loading ? <p className="muted-text">Cargando órdenes…</p> : null}
        {orders.length === 0 && !loading ? (
          <p className="muted-text">No hay órdenes registradas para la sucursal seleccionada.</p>
        ) : null}
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Proveedor</th>
                <th>Estado</th>
                <th>Creación</th>
                <th>Artículos</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id}>
                  <td>#{order.id}</td>
                  <td>{order.supplier}</td>
                  <td>
                    <span className={`badge ${order.status === "COMPLETADA" ? "success" : "neutral"}`}>
                      {statusLabels[order.status]}
                    </span>
                  </td>
                  <td>{new Date(order.created_at).toLocaleString("es-MX")}</td>
                  <td>
                    <ul className="compact-list">
                      {order.items.map((item) => (
                        <li key={item.id}>
                          Dispositivo #{item.device_id} · {item.quantity_received}/{item.quantity_ordered} unidades
                        </li>
                      ))}
                    </ul>
                  </td>
                  <td>
                    <div className="transfer-actions">
                      <button type="button" className="btn btn--ghost" onClick={() => handleReceive(order)}>
                        Recibir pendientes
                      </button>
                      <button type="button" className="btn btn--ghost" onClick={() => handleReturn(order)}>
                        Registrar devolución
                      </button>
                      <button type="button" className="btn btn--ghost" onClick={() => handleCancel(order)}>
                        Cancelar orden
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

export default Purchases;
