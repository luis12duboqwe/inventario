import { Fragment, type FormEvent } from "react";

import type { Customer, Device, RepairForm, RepairPartForm, Store } from "../../../types/repairs";

type SidePanelProps = {
  stores: Store[];
  selectedStoreId: number | null;
  form: RepairForm;
  customers: Customer[];
  devices: Device[];
  customerSearch: string;
  onCustomerSearchChange: (value: string) => void;
  onStoreChange: (storeId: number | null) => void;
  onFormChange: (updates: Partial<RepairForm>) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onReset: () => void;
  onAddPart: () => void;
  onRemovePart: (index: number) => void;
  onPartChange: (index: number, updates: Partial<RepairPartForm>) => void;
};

function SidePanel({
  stores,
  selectedStoreId,
  form,
  customers,
  devices,
  customerSearch,
  onCustomerSearchChange,
  onStoreChange,
  onFormChange,
  onSubmit,
  onReset,
  onAddPart,
  onRemovePart,
  onPartChange,
}: SidePanelProps) {
  return (
    <form className="form-grid" onSubmit={onSubmit}>
      <label>
        Sucursal
        <select
          value={selectedStoreId ?? ""}
          onChange={(event) => {
            const value = event.target.value ? Number(event.target.value) : null;
            onStoreChange(value);
            onFormChange({ storeId: value });
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
          onChange={(event) => onFormChange({ technicianName: event.target.value })}
          placeholder="Nombre del técnico"
        />
      </label>

      <label>
        Tipo de daño
        <input
          value={form.damageType}
          onChange={(event) => onFormChange({ damageType: event.target.value })}
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
          onChange={(event) => onFormChange({ laborCost: Number(event.target.value) })}
        />
      </label>

      <label>
        Cliente (búsqueda)
        <input
          value={customerSearch}
          onChange={(event) => onCustomerSearchChange(event.target.value)}
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
            onFormChange({
              customerId: value,
              customerName: selected?.name ?? form.customerName,
              customerContact: selected?.phone ?? form.customerContact,
            });
          }}
        >
          <option value="">Mostrador / sin registro</option>
          {customers.map((customer) => (
            <option key={customer.id} value={customer.id}>
              {customer.name} · Deuda $
              {customer.outstanding_debt.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </option>
          ))}
        </select>
      </label>

      <label>
        Cliente (manual)
        <input
          value={form.customerName}
          onChange={(event) => onFormChange({ customerName: event.target.value })}
          placeholder="Nombre personalizado"
        />
      </label>

      <label>
        Contacto del cliente
        <input
          value={form.customerContact}
          onChange={(event) => onFormChange({ customerContact: event.target.value })}
          placeholder="Teléfono o correo de contacto"
        />
      </label>

      <label className="wide">
        Descripción del dispositivo
        <textarea
          value={form.deviceDescription}
          onChange={(event) => onFormChange({ deviceDescription: event.target.value })}
          rows={2}
          placeholder="Modelo, color, accesorios recibidos"
        />
      </label>

      <label>
        Modelo del dispositivo
        <input
          value={form.deviceModel}
          onChange={(event) => onFormChange({ deviceModel: event.target.value })}
          placeholder="Marca y modelo reportado"
        />
      </label>

      <label>
        IMEI / Serie
        <input
          value={form.imei}
          onChange={(event) => onFormChange({ imei: event.target.value })}
          placeholder="Identificador del equipo"
        />
      </label>

      <label className="wide">
        Diagnóstico técnico
        <textarea
          value={form.diagnosis}
          onChange={(event) => onFormChange({ diagnosis: event.target.value })}
          rows={2}
          placeholder="Resultado de la evaluación técnica"
        />
      </label>

      <label className="wide">
        Notas internas
        <textarea
          value={form.notes}
          onChange={(event) => onFormChange({ notes: event.target.value })}
          rows={2}
          placeholder="Información adicional, autorización del cliente, etc."
        />
      </label>

      <div className="wide">
        <div className="actions-row">
          <span className="muted-text">Repuestos utilizados</span>
          <button type="button" className="btn btn--ghost" onClick={onAddPart}>
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
                  <th>Origen</th>
                  <th>Dispositivo</th>
                  <th>Descripción</th>
                  <th>Cantidad</th>
                  <th>Costo unitario</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {form.parts.map((part, index) => (
                  <Fragment key={`${part.deviceId ?? "nuevo"}-${index}`}>
                    <tr>
                      <td>
                        <select
                          value={part.source}
                          onChange={(event) =>
                            onPartChange(index, {
                              source: event.target.value as "STOCK" | "EXTERNAL",
                            })
                          }
                        >
                          <option value="STOCK">Inventario</option>
                          <option value="EXTERNAL">Compra externa</option>
                        </select>
                      </td>
                      <td>
                        <select
                          value={part.deviceId ?? ""}
                          onChange={(event) =>
                            onPartChange(index, {
                              deviceId: event.target.value ? Number(event.target.value) : null,
                            })
                          }
                          disabled={part.source === "EXTERNAL"}
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
                          value={part.partName}
                          onChange={(event) => onPartChange(index, { partName: event.target.value })}
                          placeholder={part.source === "EXTERNAL" ? "Nombre del repuesto" : "Etiqueta opcional"}
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          min={1}
                          value={part.quantity}
                          onChange={(event) => onPartChange(index, { quantity: Number(event.target.value) })}
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          min={0}
                          step="0.01"
                          value={part.unitCost}
                          onChange={(event) => onPartChange(index, { unitCost: Number(event.target.value) })}
                        />
                      </td>
                      <td>
                        <button type="button" className="btn btn--ghost" onClick={() => onRemovePart(index)}>
                          Quitar
                        </button>
                      </td>
                    </tr>
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="actions-row wide">
        <button type="submit" className="btn btn--primary">
          Registrar reparación
        </button>
        <button type="button" className="btn btn--ghost" onClick={onReset}>
          Limpiar formulario
        </button>
      </div>
    </form>
  );
}

export type { SidePanelProps };
export default SidePanel;
