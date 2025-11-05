import { useCallback, useEffect, useMemo, useState } from "react";
import type { PurchaseOrder, Sale, Store } from "../../../api";
import { listPurchaseOrders, listSales, registerPurchaseReturn, registerSaleReturn } from "../../../api";

type Props = {
  token: string;
  stores: Store[];
  defaultStoreId?: number | null;
  onInventoryRefresh?: () => void;
};

type PurchaseReturnForm = {
  storeId: number | null;
  orderId: number | null;
  deviceId: number | null;
  quantity: number;
  reason: string;
};

type SaleReturnForm = {
  storeId: number | null;
  saleId: number | null;
  deviceId: number | null;
  quantity: number;
  reason: string;
};

const initialPurchaseReturn: PurchaseReturnForm = {
  storeId: null,
  orderId: null,
  deviceId: null,
  quantity: 1,
  reason: "Equipo defectuoso",
};

const initialSaleReturn: SaleReturnForm = {
  storeId: null,
  saleId: null,
  deviceId: null,
  quantity: 1,
  reason: "Reingreso cliente",
};

function Returns({ token, stores, defaultStoreId = null, onInventoryRefresh }: Props) {
  // Para evitar setState en efectos cuando cambia defaultStoreId,
  // se remonta un subcomponente con key basada en el defaultStoreId.
  return (
    <ReturnsInner
      key={String(defaultStoreId ?? "none")}
      token={token}
      stores={stores}
      defaultStoreId={defaultStoreId}
      onInventoryRefresh={onInventoryRefresh}
    />
  );
}

function ReturnsInner({ token, stores, defaultStoreId = null, onInventoryRefresh }: Props) {
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([]);
  const [sales, setSales] = useState<Sale[]>([]);
  const [purchaseForm, setPurchaseForm] = useState<PurchaseReturnForm>(() => ({
    ...initialPurchaseReturn,
    storeId: defaultStoreId,
  }));
  const [saleForm, setSaleForm] = useState<SaleReturnForm>(() => ({ ...initialSaleReturn, storeId: defaultStoreId }));
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const selectedPurchaseOrder = useMemo(
    () => purchaseOrders.find((order) => order.id === purchaseForm.orderId) ?? null,
    [purchaseOrders, purchaseForm.orderId]
  );

  const selectedSale = useMemo(
    () => sales.find((sale) => sale.id === saleForm.saleId) ?? null,
    [sales, saleForm.saleId]
  );

  const refreshOrders = useCallback(async (storeId?: number | null) => {
    if (!storeId) {
      setPurchaseOrders([]);
      return;
    }
    try {
      const data = await listPurchaseOrders(token, storeId);
      setPurchaseOrders(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible cargar las órdenes de compra");
    }
  }, [token]);

  const refreshSales = useCallback(async (storeId?: number | null) => {
    if (!storeId) {
      setSales([]);
      return;
    }
    try {
      const data = await listSales(token, { storeId, limit: 100 });
      setSales(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible cargar las ventas");
    }
  }, [token]);

  useEffect(() => {
    // Evita setState sincrónico en el efecto
    Promise.resolve().then(() => {
      void refreshOrders(purchaseForm.storeId ?? undefined);
    });
  }, [purchaseForm.storeId, refreshOrders]);

  useEffect(() => {
    // Evita setState sincrónico en el efecto
    Promise.resolve().then(() => {
      void refreshSales(saleForm.storeId ?? undefined);
    });
  }, [saleForm.storeId, refreshSales]);

  const updatePurchaseForm = (updates: Partial<PurchaseReturnForm>) => {
    setPurchaseForm((current) => ({ ...current, ...updates }));
  };

  const updateSaleForm = (updates: Partial<SaleReturnForm>) => {
    setSaleForm((current) => ({ ...current, ...updates }));
  };

  const handlePurchaseReturn = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!purchaseForm.storeId || !purchaseForm.orderId || !purchaseForm.deviceId) {
      setError("Selecciona orden y dispositivo para la devolución.");
      return;
    }
    if (!purchaseForm.reason.trim() || purchaseForm.reason.trim().length < 5) {
      setError("El motivo debe contener al menos 5 caracteres.");
      return;
    }
    try {
      setError(null);
      await registerPurchaseReturn(
        token,
        purchaseForm.orderId,
        {
          device_id: purchaseForm.deviceId,
          quantity: Math.max(1, purchaseForm.quantity),
          reason: purchaseForm.reason.trim(),
        },
        purchaseForm.reason.trim()
      );
      setMessage("Devolución al proveedor registrada correctamente");
      await refreshOrders(purchaseForm.storeId);
      onInventoryRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible registrar la devolución de compra");
    }
  };

  const handleSaleReturn = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!saleForm.storeId || !saleForm.saleId || !saleForm.deviceId) {
      setError("Selecciona la venta y el dispositivo a devolver.");
      return;
    }
    if (!saleForm.reason.trim() || saleForm.reason.trim().length < 5) {
      setError("El motivo debe contener al menos 5 caracteres.");
      return;
    }
    try {
      setError(null);
      await registerSaleReturn(
        token,
        {
          sale_id: saleForm.saleId,
          items: [
            {
              device_id: saleForm.deviceId,
              quantity: Math.max(1, saleForm.quantity),
              reason: saleForm.reason.trim(),
            },
          ],
        },
        saleForm.reason.trim()
      );
      setMessage("Devolución de cliente registrada correctamente");
      await refreshSales(saleForm.storeId);
      onInventoryRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible registrar la devolución de venta");
    }
  };

  return (
    <section className="card">
      <h2>Devoluciones y ajustes</h2>
      <p className="card-subtitle">
        Registra devoluciones a proveedores y reingresos de clientes para mantener la auditoría financiera.
      </p>
      {error ? <div className="alert error">{error}</div> : null}
      {message ? <div className="alert success">{message}</div> : null}

      <div className="returns-grid">
        <form onSubmit={handlePurchaseReturn}>
          <h3>Devolución a proveedor</h3>
          <label>
            Sucursal
            <select
              value={purchaseForm.storeId ?? ""}
              onChange={(event) => updatePurchaseForm({
                storeId: event.target.value ? Number(event.target.value) : null,
                orderId: null,
                deviceId: null,
              })}
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
            Orden de compra
            <select
              value={purchaseForm.orderId ?? ""}
              onChange={(event) => updatePurchaseForm({
                orderId: event.target.value ? Number(event.target.value) : null,
                deviceId: null,
              })}
              disabled={!purchaseForm.storeId}
            >
              <option value="">Selecciona una orden</option>
              {purchaseOrders.map((order) => (
                <option key={order.id} value={order.id}>
                  #{order.id} · {order.supplier}
                </option>
              ))}
            </select>
          </label>
          <label>
            Dispositivo
            <select
              value={purchaseForm.deviceId ?? ""}
              onChange={(event) => updatePurchaseForm({
                deviceId: event.target.value ? Number(event.target.value) : null,
              })}
              disabled={!selectedPurchaseOrder}
            >
              <option value="">Selecciona un dispositivo</option>
              {selectedPurchaseOrder?.items.map((item) => (
                <option key={item.id} value={item.device_id}>
                  #{item.device_id} · {item.quantity_received}/{item.quantity_ordered} recibidos
                </option>
              ))}
            </select>
          </label>
          <label>
            Cantidad
            <input
              type="number"
              min={1}
              value={purchaseForm.quantity}
              onChange={(event) => updatePurchaseForm({ quantity: Number(event.target.value) })}
            />
          </label>
          <label>
            Motivo corporativo
            <input
              value={purchaseForm.reason}
              onChange={(event) => updatePurchaseForm({ reason: event.target.value })}
              placeholder="Describe el motivo"
            />
          </label>
          <button type="submit" className="btn btn--primary">
            Registrar devolución a proveedor
          </button>
        </form>

        <form onSubmit={handleSaleReturn}>
          <h3>Devolución de cliente</h3>
          <label>
            Sucursal
            <select
              value={saleForm.storeId ?? ""}
              onChange={(event) => updateSaleForm({
                storeId: event.target.value ? Number(event.target.value) : null,
                saleId: null,
                deviceId: null,
              })}
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
            Venta
            <select
              value={saleForm.saleId ?? ""}
              onChange={(event) => updateSaleForm({
                saleId: event.target.value ? Number(event.target.value) : null,
                deviceId: null,
              })}
              disabled={!saleForm.storeId}
            >
              <option value="">Selecciona una venta</option>
              {sales.map((sale) => (
                <option key={sale.id} value={sale.id}>
                  #{sale.id} · {new Date(sale.created_at).toLocaleString("es-MX")}
                </option>
              ))}
            </select>
          </label>
          <label>
            Dispositivo
            <select
              value={saleForm.deviceId ?? ""}
              onChange={(event) => updateSaleForm({
                deviceId: event.target.value ? Number(event.target.value) : null,
              })}
              disabled={!selectedSale}
            >
              <option value="">Selecciona un dispositivo</option>
              {selectedSale?.items.map((item) => (
                <option key={item.id} value={item.device_id}>
                  #{item.device_id} · {item.quantity} vendidos
                </option>
              ))}
            </select>
          </label>
          <label>
            Cantidad
            <input
              type="number"
              min={1}
              value={saleForm.quantity}
              onChange={(event) => updateSaleForm({ quantity: Number(event.target.value) })}
            />
          </label>
          <label>
            Motivo corporativo
            <input
              value={saleForm.reason}
              onChange={(event) => updateSaleForm({ reason: event.target.value })}
              placeholder="Describe el motivo"
            />
          </label>
          <button type="submit" className="btn btn--primary">
            Registrar devolución de cliente
          </button>
        </form>
      </div>
    </section>
  );
}

export default Returns;
