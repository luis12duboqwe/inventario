import { useCallback, useEffect, useMemo, useState } from "react";
import type { Customer, Device, RepairOrder, Store } from "../../../api";
import {
  createRepairOrder,
  deleteRepairOrder,
  downloadRepairOrderPdf,
  getDevices,
  listCustomers,
  listRepairOrders,
  updateRepairOrder,
} from "../../../api";

type Props = {
  token: string;
  stores: Store[];
  defaultStoreId?: number | null;
  onInventoryRefresh?: () => void;
};

type RepairPartForm = {
  deviceId: number | null;
  quantity: number;
  unitCost: number;
};

type RepairForm = {
  storeId: number | null;
  customerId: number | null;
  customerName: string;
  technicianName: string;
  damageType: string;
  deviceDescription: string;
  notes: string;
  laborCost: number;
  parts: RepairPartForm[];
};

const initialForm: RepairForm = {
  storeId: null,
  customerId: null,
  customerName: "",
  technicianName: "",
  damageType: "",
  deviceDescription: "",
  notes: "",
  laborCost: 0,
  parts: [],
};

const statusLabels: Record<RepairOrder["status"], string> = {
  PENDIENTE: "🟡 Pendiente",
  EN_PROCESO: "🟠 En proceso",
  LISTO: "🟢 Listo",
  ENTREGADO: "⚪ Entregado",
};

const statusOptions: Array<RepairOrder["status"]> = [
  "PENDIENTE",
  "EN_PROCESO",
  "LISTO",
  "ENTREGADO",
];

function RepairOrders({ token, stores, defaultStoreId = null, onInventoryRefresh }: Props) {
  const [orders, setOrders] = useState<RepairOrder[]>([]);
  const [form, setForm] = useState<RepairForm>({ ...initialForm, storeId: defaultStoreId ?? null });
  const [devices, setDevices] = useState<Device[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [customerSearch, setCustomerSearch] = useState("");
  const [selectedStoreId, setSelectedStoreId] = useState<number | null>(defaultStoreId ?? null);
  const [statusFilter, setStatusFilter] = useState<RepairOrder["status"] | "TODOS">("TODOS");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshOrders = useCallback(
    async (storeId?: number | null, query?: string, status?: RepairOrder["status"] | "TODOS") => {
      try {
        setLoading(true);
        const params: { store_id?: number; status?: string; q?: string; limit?: number } = { limit: 100 };
        if (storeId) {
          params.store_id = storeId;
        }
        if (status && status !== "TODOS") {
          params.status = status;
        }
        const trimmed = query?.trim();
        if (trimmed) {
          params.q = trimmed;
        }
        const data = await listRepairOrders(token, params);
        setOrders(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible cargar las órdenes de reparación.");
      } finally {
        setLoading(false);
      }
    },
    [token]
  );

  const refreshDevices = useCallback(
    async (storeId: number | null) => {
      if (!storeId) {
        setDevices([]);
        return;
      }
      try {
        const storeDevices = await getDevices(token, storeId);
        setDevices(storeDevices);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible cargar los dispositivos de la sucursal.");
      }
    },
    [token]
  );

  const refreshCustomers = useCallback(
    async (query?: string) => {
      try {
        const trimmed = query?.trim();
        const results = await listCustomers(token, trimmed && trimmed.length > 0 ? trimmed : undefined, 100);
        setCustomers(results);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible cargar los clientes para reparaciones.");
      }
    },
    [token]
  );

  useEffect(() => {
    setSelectedStoreId(defaultStoreId ?? null);
    setForm((current) => ({ ...current, storeId: defaultStoreId ?? null }));
  }, [defaultStoreId]);

  useEffect(() => {
    const trimmed = search.trim();
    const handler = window.setTimeout(() => {
      void refreshOrders(selectedStoreId, trimmed, statusFilter);
    }, 350);
    return () => window.clearTimeout(handler);
  }, [search, statusFilter, selectedStoreId, refreshOrders]);

  useEffect(() => {
    const trimmed = customerSearch.trim();
    const handler = window.setTimeout(() => {
      void refreshCustomers(trimmed.length >= 2 ? trimmed : undefined);
    }, 350);
    return () => window.clearTimeout(handler);
  }, [customerSearch, refreshCustomers]);

  useEffect(() => {
    void refreshCustomers();
  }, [refreshCustomers]);

  useEffect(() => {
    if (!selectedStoreId) {
      setOrders([]);
      setDevices([]);
      setForm((current) => ({ ...current, storeId: null, parts: [] }));
      return;
    }
    void refreshOrders(selectedStoreId, search.trim(), statusFilter);
    void refreshDevices(selectedStoreId);
    setForm((current) => ({ ...current, storeId: selectedStoreId }));
  }, [selectedStoreId, refreshDevices, refreshOrders, search, statusFilter]);

  const updateForm = (updates: Partial<RepairForm>) => {
    setForm((current) => ({ ...current, ...updates }));
  };

  const updatePart = (index: number, updates: Partial<RepairPartForm>) => {
    setForm((current) => ({
      ...current,
      parts: current.parts.map((part, position) =>
        position === index ? { ...part, ...updates } : part
      ),
    }));
  };

  const addPart = () => {
    setForm((current) => ({
      ...current,
      parts: [...current.parts, { deviceId: null, quantity: 1, unitCost: 0 }],
    }));
  };

  const removePart = (index: number) => {
    setForm((current) => ({
      ...current,
      parts: current.parts.filter((_, position) => position !== index),
    }));
  };

  const askReason = (promptText: string): string | null => {
    const reason = window.prompt(promptText, "");
    if (!reason || reason.trim().length < 5) {
      setError("Debes indicar un motivo corporativo válido (mínimo 5 caracteres).");
      return null;
    }
    return reason.trim();
  };

  const handleCreate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form.storeId) {
      setError("Selecciona la sucursal donde se registrará la reparación.");
      return;
    }
    if (!form.technicianName.trim()) {
      setError("Indica el técnico responsable de la orden.");
      return;
    }
    if (!form.damageType.trim()) {
      setError("Describe el tipo de daño reportado.");
      return;
    }
    const reason = askReason("Motivo corporativo para registrar la reparación");
    if (!reason) {
      return;
    }
    const partsPayload = form.parts
      .filter((part) => part.deviceId && part.quantity > 0)
      .map((part) => ({
        device_id: part.deviceId as number,
        quantity: Math.max(1, part.quantity),
        unit_cost: Number.isFinite(part.unitCost) ? Math.max(0, part.unitCost) : 0,
      }));
    const payload = {
      store_id: form.storeId,
      customer_id: form.customerId ?? undefined,
      customer_name: form.customerName.trim() || undefined,
      technician_name: form.technicianName.trim(),
      damage_type: form.damageType.trim(),
      device_description: form.deviceDescription.trim() || undefined,
      notes: form.notes.trim() || undefined,
      labor_cost: Number.isFinite(form.laborCost) ? Math.max(0, form.laborCost) : 0,
      parts: partsPayload,
    };
    try {
      setError(null);
      await createRepairOrder(token, payload, reason);
      setMessage("Orden de reparación registrada correctamente.");
      setForm((current) => ({ ...initialForm, storeId: current.storeId }));
      await refreshOrders(form.storeId, search.trim(), statusFilter);
      onInventoryRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible registrar la orden de reparación.");
    }
  };

  const handleStatusChange = async (order: RepairOrder, status: RepairOrder["status"]) => {
    if (status === order.status) {
      return;
    }
    const reason = askReason("Motivo corporativo para actualizar el estado de la reparación");
    if (!reason) {
      return;
    }
    try {
      await updateRepairOrder(token, order.id, { status }, reason);
      setMessage("Estado de reparación actualizado.");
      await refreshOrders(selectedStoreId, search.trim(), statusFilter);
      onInventoryRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible actualizar la reparación.");
    }
  };

  const handleDelete = async (order: RepairOrder) => {
    if (!window.confirm(`¿Eliminar la reparación #${order.id}?`)) {
      return;
    }
    const reason = askReason("Motivo corporativo para eliminar la orden de reparación");
    if (!reason) {
      return;
    }
    try {
      await deleteRepairOrder(token, order.id, reason);
      setMessage("Orden de reparación eliminada.");
      await refreshOrders(selectedStoreId, search.trim(), statusFilter);
      onInventoryRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible eliminar la orden de reparación.");
    }
  };

  const handleDownload = async (order: RepairOrder) => {
    try {
      const blob = await downloadRepairOrderPdf(token, order.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `orden_reparacion_${order.id}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible descargar la orden en PDF.");
    }
  };

  const devicesById = useMemo(() => {
    const map = new Map<number, Device>();
    devices.forEach((device) => map.set(device.id, device));
    return map;
  }, [devices]);

  return (
    <section className="card wide">
      <h2>Órdenes de reparación</h2>
      <p className="card-subtitle">
        Gestiona reparaciones con control de piezas, técnicos, estados y descarga inmediata de órdenes en PDF.
      </p>
      {message ? <div className="alert success">{message}</div> : null}
      {error ? <div className="alert error">{error}</div> : null}
      <form className="form-grid" onSubmit={handleCreate}>
        <label>
          Sucursal
          <select
            value={form.storeId ?? ""}
            onChange={(event) => {
              const value = event.target.value ? Number(event.target.value) : null;
              setSelectedStoreId(value);
              updateForm({ storeId: value });
            }}
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
          Técnico responsable
          <input
            value={form.technicianName}
            onChange={(event) => updateForm({ technicianName: event.target.value })}
            placeholder="Nombre del técnico"
          />
        </label>
        <label>
          Tipo de daño
          <input
            value={form.damageType}
            onChange={(event) => updateForm({ damageType: event.target.value })}
            placeholder="Pantalla rota, batería, humedad..."
          />
        </label>
        <label>
          Costo de mano de obra
          <input
            type="number"
            min={0}
            step="0.01"
            value={form.laborCost}
            onChange={(event) => updateForm({ laborCost: Number(event.target.value) })}
          />
        </label>
        <label>
          Cliente (búsqueda)
          <input
            value={customerSearch}
            onChange={(event) => setCustomerSearch(event.target.value)}
            placeholder="Nombre o correo del cliente"
          />
          <span className="muted-text">Escribe al menos 2 caracteres para filtrar.</span>
        </label>
        <label>
          Cliente registrado
          <select
            value={form.customerId ?? ""}
            onChange={(event) => {
              const value = event.target.value ? Number(event.target.value) : null;
              const selected = value ? customers.find((customer) => customer.id === value) : null;
              updateForm({
                customerId: value,
                customerName: selected?.name ?? form.customerName,
              });
            }}
          >
            <option value="">Mostrador / sin registro</option>
            {customers.map((customer) => (
              <option key={customer.id} value={customer.id}>
                {customer.name} · Deuda ${customer.outstanding_debt.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </option>
            ))}
          </select>
        </label>
        <label>
          Cliente (manual)
          <input
            value={form.customerName}
            onChange={(event) => updateForm({ customerName: event.target.value })}
            placeholder="Nombre personalizado"
          />
        </label>
        <label className="wide">
          Descripción del dispositivo
          <textarea
            value={form.deviceDescription}
            onChange={(event) => updateForm({ deviceDescription: event.target.value })}
            rows={2}
            placeholder="Modelo, color, accesorios recibidos"
          />
        </label>
        <label className="wide">
          Notas internas
          <textarea
            value={form.notes}
            onChange={(event) => updateForm({ notes: event.target.value })}
            rows={2}
            placeholder="Información adicional, autorización del cliente, etc."
          />
        </label>
        <div className="wide">
          <div className="actions-row">
            <span className="muted-text">Repuestos utilizados</span>
            <button type="button" className="button ghost" onClick={addPart}>
              Agregar pieza
            </button>
          </div>
          {form.parts.length === 0 ? (
            <p className="muted-text">Agrega piezas para descontarlas automáticamente del inventario.</p>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Dispositivo</th>
                    <th>Cantidad</th>
                    <th>Costo unitario</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {form.parts.map((part, index) => (
                    <tr key={index}>
                      <td>
                        <select
                          value={part.deviceId ?? ""}
                          onChange={(event) =>
                            updatePart(index, {
                              deviceId: event.target.value ? Number(event.target.value) : null,
                            })
                          }
                        >
                          <option value="">Selecciona dispositivo</option>
                          {devices.map((device) => (
                            <option key={device.id} value={device.id}>
                              {device.sku} · {device.name} ({device.quantity} disp.)
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <input
                          type="number"
                          min={1}
                          value={part.quantity}
                          onChange={(event) => updatePart(index, { quantity: Number(event.target.value) })}
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          min={0}
                          step="0.01"
                          value={part.unitCost}
                          onChange={(event) => updatePart(index, { unitCost: Number(event.target.value) })}
                        />
                      </td>
                      <td>
                        <button type="button" className="button link" onClick={() => removePart(index)}>
                          Quitar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        <div className="actions-row wide">
          <button type="submit" className="button primary">
            Registrar reparación
          </button>
          <button type="button" className="button ghost" onClick={() => setForm((current) => ({ ...initialForm, storeId: current.storeId }))}>
            Limpiar formulario
          </button>
        </div>
      </form>
      <div className="form-grid">
        <label>
          Filtrar por estado
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as RepairOrder["status"] | "TODOS")}
          >
            <option value="TODOS">Todos</option>
            {statusOptions.map((status) => (
              <option key={status} value={status}>
                {statusLabels[status]}
              </option>
            ))}
          </select>
        </label>
        <label>
          Buscar
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Cliente, técnico, daño o folio"
          />
        </label>
        <div>
          <span className="muted-text">Órdenes registradas</span>
          <strong>{orders.length}</strong>
        </div>
      </div>
      {loading ? (
        <p className="muted-text">Cargando órdenes de reparación...</p>
      ) : orders.length === 0 ? (
        <p className="muted-text">No hay órdenes con los filtros actuales.</p>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Folio</th>
                <th>Cliente</th>
                <th>Técnico</th>
                <th>Daño</th>
                <th>Estado</th>
                <th>Total</th>
                <th>Actualizado</th>
                <th>Inventario</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => {
                const updatedAt = new Date(order.updated_at).toLocaleString("es-MX");
                const total = Number(order.total_cost ?? 0).toLocaleString("es-MX", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                });
                return (
                  <tr key={order.id}>
                    <td>#{order.id}</td>
                    <td>{order.customer_name ?? "Mostrador"}</td>
                    <td>{order.technician_name}</td>
                    <td>
                      <div>{order.damage_type}</div>
                      {order.device_description ? (
                        <div className="muted-text">{order.device_description}</div>
                      ) : null}
                      {order.parts.length > 0 ? (
                        <ul className="muted-text">
                          {order.parts.map((part) => {
                            const device = devicesById.get(part.device_id);
                            return (
                              <li key={`${order.id}-${part.id}`}>
                                {part.quantity} × {device ? `${device.sku} · ${device.name}` : `Dispositivo #${part.device_id}`} (${part.unit_cost.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })})
                              </li>
                            );
                          })}
                        </ul>
                      ) : null}
                    </td>
                    <td>
                      <select
                        value={order.status}
                        onChange={(event) =>
                          handleStatusChange(order, event.target.value as RepairOrder["status"])
                        }
                      >
                        {statusOptions.map((status) => (
                          <option key={status} value={status}>
                            {statusLabels[status]}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>${total}</td>
                    <td>{updatedAt}</td>
                    <td>{order.inventory_adjusted ? "Sí" : "Pendiente"}</td>
                    <td>
                      <div className="actions-row">
                        <button type="button" className="button link" onClick={() => handleDownload(order)}>
                          PDF
                        </button>
                        <button type="button" className="button link" onClick={() => handleDelete(order)}>
                          Eliminar
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default RepairOrders;
