import type { FormEvent } from "react";
import type {
  Device,
  PurchaseOrder,
  RecurringOrder,
  Store,
} from "../../../../api";
import type { PurchaseForm } from "../../../../types/purchases";

type PurchasesOrdersPanelProps = {
  form: PurchaseForm;
  stores: Store[];
  devices: Device[];
  selectedStore: Store | null;
  templateName: string;
  templateDescription: string;
  csvLoading: boolean;
  templateSaving: boolean;
  recurringLoading: boolean;
  orders: PurchaseOrder[];
  ordersLoading: boolean;
  recurringOrders: RecurringOrder[];
  statusLabels: Record<PurchaseOrder["status"], string>;
  onUpdateForm: (updates: Partial<PurchaseForm>) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onImportCsv: (event: FormEvent<HTMLFormElement>) => void;
  onTemplateNameChange: (value: string) => void;
  onTemplateDescriptionChange: (value: string) => void;
  onSaveTemplate: (event: FormEvent<HTMLFormElement>) => void;
  onApplyTemplate: (template: RecurringOrder) => void;
  onExecuteTemplate: (template: RecurringOrder) => void;
  getTemplateSupplier: (template: RecurringOrder) => string;
  onReceive: (order: PurchaseOrder) => void;
  onReturn: (order: PurchaseOrder) => void;
  onCancel: (order: PurchaseOrder) => void;
};

const PurchasesOrdersPanel = ({
  form,
  stores,
  devices,
  selectedStore,
  templateName,
  templateDescription,
  csvLoading,
  templateSaving,
  recurringLoading,
  orders,
  ordersLoading,
  recurringOrders,
  statusLabels,
  onUpdateForm,
  onSubmit,
  onImportCsv,
  onTemplateNameChange,
  onTemplateDescriptionChange,
  onSaveTemplate,
  onApplyTemplate,
  onExecuteTemplate,
  getTemplateSupplier,
  onReceive,
  onReturn,
  onCancel,
}: PurchasesOrdersPanelProps) => {
  return (
    <section className="card">
      <h2>Órdenes de compra</h2>
      <p className="card-subtitle">
        Captura nuevas órdenes, recibe productos parciales y conserva un historial auditado de compras.
      </p>
      <form className="form-grid" onSubmit={onSubmit}>
        <label>
          Sucursal
          <select
            value={form.storeId ?? ""}
            onChange={(event) => onUpdateForm({ storeId: event.target.value ? Number(event.target.value) : null })}
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
            onChange={(event) => onUpdateForm({ supplier: event.target.value })}
            placeholder="Proveedor corporativo"
          />
        </label>
        <label>
          Dispositivo
          <select
            value={form.deviceId ?? ""}
            onChange={(event) => onUpdateForm({ deviceId: event.target.value ? Number(event.target.value) : null })}
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
            onChange={(event) => onUpdateForm({ quantity: Number(event.target.value) })}
          />
        </label>
        <label>
          Costo unitario MXN
          <input
            type="number"
            min={0}
            step="0.01"
            value={form.unitCost}
            onChange={(event) => onUpdateForm({ unitCost: Number(event.target.value) })}
          />
        </label>
        <button type="submit" className="btn btn--primary">
          Registrar orden
        </button>
      </form>

      <div className="section-divider">
        <h3>Plantillas recurrentes y carga masiva</h3>
        <div className="section-grid">
          <form className="form-grid" onSubmit={onImportCsv}>
            <label className="form-span">
              Archivo CSV
              <input type="file" name="csvFile" accept=".csv" required />
            </label>
            <button type="submit" className="btn btn--secondary" disabled={csvLoading}>
              {csvLoading ? "Importando…" : "Importar CSV"}
            </button>
            <p className="muted-text form-span">
              Columnas esperadas: <code>store_id,supplier,device_id,quantity,unit_cost[,reference][,notes]</code>
            </p>
          </form>

          <form className="form-grid" onSubmit={onSaveTemplate}>
            <label>
              Nombre de la plantilla
              <input
                type="text"
                value={templateName}
                onChange={(event) => onTemplateNameChange(event.target.value)}
                minLength={3}
                required
              />
            </label>
            <label>
              Descripción
              <input
                type="text"
                value={templateDescription}
                onChange={(event) => onTemplateDescriptionChange(event.target.value)}
                placeholder="Opcional"
              />
            </label>
            <button type="submit" className="btn btn--secondary" disabled={templateSaving}>
              {templateSaving ? "Guardando…" : "Guardar como plantilla"}
            </button>
            <p className="muted-text form-span">
              Se utilizarán los datos actuales del formulario para generar la plantilla recurrente.
            </p>
          </form>
        </div>

        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Proveedor base</th>
                <th>Último uso</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {recurringLoading ? (
                <tr>
                  <td colSpan={4} className="muted-text">
                    Cargando plantillas…
                  </td>
                </tr>
              ) : recurringOrders.length === 0 ? (
                <tr>
                  <td colSpan={4} className="muted-text">
                    Aún no hay plantillas registradas para compras.
                  </td>
                </tr>
              ) : (
                recurringOrders.map((template) => (
                  <tr key={template.id}>
                    <td>{template.name}</td>
                    <td>{getTemplateSupplier(template)}</td>
                    <td>
                      {template.last_used_at
                        ? new Date(template.last_used_at).toLocaleString("es-MX")
                        : "Nunca"}
                    </td>
                    <td>
                      <div className="transfer-actions">
                        <button
                          type="button"
                          className="btn btn--ghost"
                          onClick={() => onApplyTemplate(template)}
                        >
                          Usar datos
                        </button>
                        <button
                          type="button"
                          className="btn btn--primary"
                          onClick={() => onExecuteTemplate(template)}
                        >
                          Ejecutar
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="section-divider">
        <h3>Historial reciente</h3>
        {ordersLoading ? <p className="muted-text">Cargando órdenes…</p> : null}
        {orders.length === 0 && !ordersLoading ? (
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
                      <button type="button" className="btn btn--ghost" onClick={() => onReceive(order)}>
                        Recibir pendientes
                      </button>
                      <button type="button" className="btn btn--ghost" onClick={() => onReturn(order)}>
                        Registrar devolución
                      </button>
                      <button type="button" className="btn btn--ghost" onClick={() => onCancel(order)}>
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
};

export default PurchasesOrdersPanel;
