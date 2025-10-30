import { useEffect, useMemo, useState, type FormEvent } from "react";

import type { Device, RepairOrder, RepairOrderPartsPayload } from "../../../api";
import Modal from "../../../shared/components/ui/Modal";

type PartsModalProps = {
  order: RepairOrder | null;
  open: boolean;
  onClose: () => void;
  resolveDeviceLabel: (deviceId: number) => string;
  devices: Device[];
  onAppendParts: (
    order: RepairOrder,
    parts: RepairOrderPartsPayload["parts"],
  ) => Promise<boolean>; // [PACK37-frontend]
  onRemovePart: (order: RepairOrder, partId: number) => Promise<boolean>; // [PACK37-frontend]
};

type ManagePartForm = {
  source: "STOCK" | "EXTERNAL";
  deviceId: number | null;
  partName: string;
  quantity: number;
  unitCost: number;
};

const initialPartForm: ManagePartForm = {
  source: "STOCK",
  deviceId: null,
  partName: "",
  quantity: 1,
  unitCost: 0,
};

function PartsModal({
  order,
  open,
  onClose,
  resolveDeviceLabel,
  devices,
  onAppendParts,
  onRemovePart,
}: PartsModalProps) {
  if (!order) {
    return null;
  }

  const [form, setForm] = useState<ManagePartForm>(initialPartForm);
  const [searchTerm, setSearchTerm] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setForm(initialPartForm);
    setSearchTerm("");
    setError(null);
  }, [order?.id, open]);

  const filteredDevices = useMemo(() => {
    if (!searchTerm.trim()) {
      return devices;
    }
    const normalized = searchTerm.trim().toLowerCase();
    return devices.filter((device) => {
      const terms = [
        device.sku,
        device.name,
        device.imei ?? "",
        device.serial ?? "",
        device.modelo ?? "",
        device.marca ?? "",
      ]
        .filter(Boolean)
        .map((term) => term!.toString().toLowerCase());
      return terms.some((term) => term.includes(normalized));
    });
  }, [devices, searchTerm]); // [PACK37-frontend]

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!order) {
      return;
    }
    setError(null);
    const quantity = Number.isFinite(form.quantity) ? Math.max(1, Math.floor(form.quantity)) : 1;
    const unitCost = Number.isFinite(form.unitCost) ? Math.max(0, form.unitCost) : 0;
    if (form.source === "STOCK" && !form.deviceId) {
      setError("Selecciona un dispositivo del inventario para descontar la pieza.");
      return;
    }
    const trimmedName = form.partName.trim();
    if (form.source === "EXTERNAL" && trimmedName.length === 0) {
      setError("Describe el repuesto externo para registrarlo correctamente.");
      return;
    }
    const payloadPart: RepairOrderPartsPayload["parts"][number] = {
      source: form.source,
      quantity,
      unit_cost: unitCost,
    };
    if (form.source === "STOCK" && form.deviceId) {
      payloadPart.device_id = form.deviceId;
    }
    if (trimmedName) {
      payloadPart.part_name = trimmedName;
    }
    const success = await onAppendParts(order, [payloadPart]);
    if (!success) {
      setError("No fue posible registrar el repuesto. Verifica inventario y vuelve a intentar.");
      return;
    }
    setForm((current) => ({ ...initialPartForm, source: current.source }));
  };

  const handleRemove = async (partId: number) => {
    if (!order) {
      return;
    }
    const success = await onRemovePart(order, partId);
    if (!success) {
      setError("No fue posible quitar el repuesto seleccionado.");
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Repuestos utilizados · #${order.id}`}
      description="Detalle de piezas descontadas del inventario para la orden seleccionada."
      size="lg"
    >
      <div className="parts-modal__content">
        {error ? <div className="alert error">{error}</div> : null}
        <section>
          <h3>Repuestos registrados</h3>
          {order.parts.length === 0 ? (
            <p className="muted-text">No se registraron repuestos para esta reparación.</p>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Repuesto</th>
                    <th>Origen</th>
                    <th>Cantidad</th>
                    <th>Costo unitario</th>
                    <th>Total</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {order.parts.map((part) => {
                    const label = part.part_name
                      ? part.part_name
                      : part.device_id
                      ? resolveDeviceLabel(part.device_id)
                      : "Repuesto externo";
                    const total = Number(part.unit_cost ?? 0) * Number(part.quantity ?? 0);
                    return (
                      <tr key={`${order.id}-${part.id ?? `${part.device_id}-${part.quantity}`}`}>
                        <td>{label}</td>
                        <td>{part.source === "EXTERNAL" ? "Compra externa" : "Inventario"}</td>
                        <td>{part.quantity}</td>
                        <td>
                          $
                          {Number(part.unit_cost ?? 0).toLocaleString("es-MX", {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}
                        </td>
                        <td>
                          ${total.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>
                        <td>
                          {typeof part.id === "number" ? (
                            <button
                              type="button"
                              className="btn btn--ghost"
                              onClick={() => void handleRemove(part.id as number)}
                            >
                              Quitar
                            </button>
                          ) : null}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section>
          <h3>Agregar repuesto</h3>
          <form className="form-grid" onSubmit={handleSubmit}>
            <label>
              Origen
              <select
                value={form.source}
                onChange={(event) =>
                  setForm((current) => ({ ...current, source: event.target.value as "STOCK" | "EXTERNAL" }))
                }
              >
                <option value="STOCK">Inventario</option>
                <option value="EXTERNAL">Compra externa</option>
              </select>
            </label>

            {form.source === "STOCK" ? (
              <label className="wide">
                Buscar dispositivo (SKU, IMEI, nombre)
                <input
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  placeholder="Pantalla, batería, SKU…"
                />
              </label>
            ) : null}

            <label className="wide">
              {form.source === "STOCK" ? "Dispositivo" : "Descripción"}
              {form.source === "STOCK" ? (
                <select
                  value={form.deviceId ?? ""}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      deviceId: event.target.value ? Number(event.target.value) : null,
                      partName: current.partName,
                    }))
                  }
                >
                  <option value="">Selecciona dispositivo</option>
                  {filteredDevices.length === 0 ? (
                    <option value="" disabled>
                      Sin coincidencias con la búsqueda
                    </option>
                  ) : null}
                  {filteredDevices.map((device) => (
                    <option key={device.id} value={device.id}>
                      {device.sku} · {device.name} ({device.quantity} disp.)
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  value={form.partName}
                  onChange={(event) => setForm((current) => ({ ...current, partName: event.target.value }))}
                  placeholder="Nombre del repuesto"
                />
              )}
            </label>

            {form.source === "STOCK" ? (
              <label className="wide">
                Descripción opcional
                <input
                  value={form.partName}
                  onChange={(event) => setForm((current) => ({ ...current, partName: event.target.value }))}
                  placeholder="Etiqueta personalizada"
                />
              </label>
            ) : null}

            <label>
              Cantidad
              <input
                type="number"
                min={1}
                value={form.quantity}
                onChange={(event) => setForm((current) => ({ ...current, quantity: Number(event.target.value) }))}
              />
            </label>

            <label>
              Costo unitario
              <input
                type="number"
                min={0}
                step="0.01"
                value={form.unitCost}
                onChange={(event) => setForm((current) => ({ ...current, unitCost: Number(event.target.value) }))}
              />
            </label>

            <div className="actions-row wide">
              <button type="submit" className="btn btn--primary">
                Agregar repuesto
              </button>
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => setForm((current) => ({ ...initialPartForm, source: current.source }))}
              >
                Limpiar formulario
              </button>
            </div>
          </form>
        </section>
      </div>
    </Modal>
  );
}

export type { PartsModalProps };
export default PartsModal;
