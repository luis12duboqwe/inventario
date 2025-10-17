import { useEffect, useMemo, useState } from "react";
import type { Device, Sale, Store } from "../../../api";
import { createSale, getDevices, listSales } from "../../../api";

const paymentLabels: Record<Sale["payment_method"], string> = {
  EFECTIVO: "Efectivo",
  TARJETA: "Tarjeta",
  TRANSFERENCIA: "Transferencia",
  OTRO: "Otro",
};

type Props = {
  token: string;
  stores: Store[];
  defaultStoreId?: number | null;
  onInventoryRefresh?: () => void;
};

type SaleForm = {
  storeId: number | null;
  deviceId: number | null;
  quantity: number;
  paymentMethod: Sale["payment_method"];
  discountPercent: number;
  customerName: string;
  notes: string;
  reason: string;
};

const initialForm: SaleForm = {
  storeId: null,
  deviceId: null,
  quantity: 1,
  paymentMethod: "EFECTIVO",
  discountPercent: 0,
  customerName: "",
  notes: "",
  reason: "Venta mostrador",
};

function Sales({ token, stores, defaultStoreId = null, onInventoryRefresh }: Props) {
  const [sales, setSales] = useState<Sale[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [form, setForm] = useState<SaleForm>({ ...initialForm, storeId: defaultStoreId });
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const selectedStore = useMemo(
    () => stores.find((store) => store.id === form.storeId) ?? null,
    [stores, form.storeId]
  );

  const refreshSales = async (storeId?: number | null) => {
    if (!storeId) {
      setSales([]);
      return;
    }
    try {
      const data = await listSales(token, storeId);
      setSales(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible cargar las ventas");
    }
  };

  useEffect(() => {
    setForm((current) => ({ ...current, storeId: defaultStoreId ?? null }));
  }, [defaultStoreId]);

  useEffect(() => {
    refreshSales(form.storeId ?? undefined);
  }, [form.storeId, token]);

  useEffect(() => {
    const loadDevices = async () => {
      if (!form.storeId) {
        setDevices([]);
        return;
      }
      try {
        const data = await getDevices(token, form.storeId, { estado_inventario: "disponible" });
        setDevices(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible cargar los dispositivos");
      }
    };
    loadDevices();
  }, [form.storeId, token]);

  const updateForm = (updates: Partial<SaleForm>) => {
    setForm((current) => ({ ...current, ...updates }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form.storeId || !form.deviceId) {
      setError("Selecciona sucursal y dispositivo.");
      return;
    }
    if (!form.reason.trim() || form.reason.trim().length < 5) {
      setError("El motivo corporativo debe tener al menos 5 caracteres.");
      return;
    }
    try {
      setError(null);
      await createSale(
        token,
        {
          store_id: form.storeId,
          items: [{ device_id: form.deviceId, quantity: Math.max(1, form.quantity) }],
          payment_method: form.paymentMethod,
          discount_percent: Math.max(0, form.discountPercent),
          customer_name: form.customerName || undefined,
          notes: form.notes || undefined,
        },
        form.reason.trim()
      );
      setMessage("Venta registrada correctamente");
      setForm((current) => ({ ...initialForm, storeId: current.storeId }));
      await refreshSales(form.storeId);
      onInventoryRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible registrar la venta");
    }
  };

  return (
    <section className="card">
      <h2>Ventas rápidas</h2>
      <p className="card-subtitle">Da salida al inventario con control de descuentos y métodos de pago.</p>
      {error ? <div className="alert error">{error}</div> : null}
      {message ? <div className="alert success">{message}</div> : null}
      <form className="form-grid" onSubmit={handleSubmit}>
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
          Cantidad
          <input
            type="number"
            min={1}
            value={form.quantity}
            onChange={(event) => updateForm({ quantity: Number(event.target.value) })}
          />
        </label>
        <label>
          Método de pago
          <select
            value={form.paymentMethod}
            onChange={(event) => updateForm({ paymentMethod: event.target.value as Sale["payment_method"] })}
          >
            {Object.entries(paymentLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Descuento (%)
          <input
            type="number"
            min={0}
            max={100}
            value={form.discountPercent}
            onChange={(event) => updateForm({ discountPercent: Number(event.target.value) })}
          />
        </label>
        <label>
          Cliente (opcional)
          <input
            value={form.customerName}
            onChange={(event) => updateForm({ customerName: event.target.value })}
            placeholder="Nombre del cliente"
          />
        </label>
        <label>
          Nota interna
          <input
            value={form.notes}
            onChange={(event) => updateForm({ notes: event.target.value })}
            placeholder="Observaciones"
          />
        </label>
        <label>
          Motivo corporativo
          <input
            value={form.reason}
            onChange={(event) => updateForm({ reason: event.target.value })}
            placeholder="Motivo para auditoría"
          />
        </label>
        <button type="submit" className="btn btn--primary">
          Registrar venta
        </button>
      </form>

      <div className="section-divider">
        <h3>Ventas registradas</h3>
        {sales.length === 0 ? (
          <p className="muted-text">Aún no se registran ventas para la sucursal seleccionada.</p>
        ) : (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Cliente</th>
                  <th>Método</th>
                  <th>Total</th>
                  <th>Creación</th>
                  <th>Artículos</th>
                </tr>
              </thead>
              <tbody>
                {sales.map((sale) => (
                  <tr key={sale.id}>
                    <td>#{sale.id}</td>
                    <td>{sale.customer_name ?? "Mostrador"}</td>
                    <td>{paymentLabels[sale.payment_method]}</td>
                    <td>${sale.total_amount.toFixed(2)}</td>
                    <td>{new Date(sale.created_at).toLocaleString("es-MX")}</td>
                    <td>
                      <ul className="compact-list">
                        {sale.items.map((item) => (
                          <li key={item.id}>
                            Dispositivo #{item.device_id} · {item.quantity} uds — Línea {item.total_line.toFixed(2)} MXN
                          </li>
                        ))}
                      </ul>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}

export default Sales;
