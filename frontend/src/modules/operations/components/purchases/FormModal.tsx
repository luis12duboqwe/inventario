import type { FormEvent } from "react";
import type { Device } from "@api/inventory";
import type { PurchaseVendor } from "@api/purchases";
import type { Store } from "@api/stores";
import type { PurchaseRecordDraftItem, PurchaseRecordForm } from "../../../../types/purchases";

type PurchasesFormModalProps = {
  vendors: PurchaseVendor[];
  stores: Store[];
  devices: Device[];
  recordForm: PurchaseRecordForm;
  recordItems: PurchaseRecordDraftItem[];
  paymentOptions: readonly string[];
  recordStatusOptions: readonly string[];
  recordSubtotal: number;
  recordTax: number;
  recordTotal: number;
  currencyFormatter: Intl.NumberFormat;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onUpdateRecordForm: (updates: Partial<PurchaseRecordForm>) => void;
  onUpdateRecordItem: (index: number, updates: Partial<PurchaseRecordDraftItem>) => void;
  onAddRecordItem: () => void;
  onRemoveRecordItem: (index: number) => void;
};

const PurchasesFormModal = ({
  vendors,
  stores,
  devices,
  recordForm,
  recordItems,
  paymentOptions,
  recordStatusOptions,
  recordSubtotal,
  recordTax,
  recordTotal,
  currencyFormatter,
  onSubmit,
  onUpdateRecordForm,
  onUpdateRecordItem,
  onAddRecordItem,
  onRemoveRecordItem,
}: PurchasesFormModalProps) => {
  return (
    <section className="card">
      <h2>Registro directo de compras</h2>
      <p className="card-subtitle">
        Captura compras inmediatas con impuestos calculados automáticamente y vínculos al inventario
        seleccionado.
      </p>
      <form className="form-grid" onSubmit={onSubmit}>
        <label>
          Proveedor
          <select
            value={recordForm.vendorId ?? ""}
            onChange={(event) =>
              onUpdateRecordForm({
                vendorId: event.target.value ? Number(event.target.value) : null,
              })
            }
          >
            <option value="">Selecciona un proveedor</option>
            {vendors.map((vendor) => (
              <option key={vendor.id_proveedor} value={vendor.id_proveedor}>
                {vendor.nombre}
              </option>
            ))}
          </select>
        </label>
        <label>
          Sucursal de referencia
          <select
            value={recordForm.storeId ?? ""}
            onChange={(event) =>
              onUpdateRecordForm({
                storeId: event.target.value ? Number(event.target.value) : null,
              })
            }
          >
            <option value="">Opcional</option>
            {stores.map((store) => (
              <option key={store.id} value={store.id}>
                {store.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Método de pago
          <select
            value={recordForm.paymentMethod}
            onChange={(event) => onUpdateRecordForm({ paymentMethod: event.target.value })}
          >
            {paymentOptions.map((method) => (
              <option key={method} value={method}>
                {method}
              </option>
            ))}
          </select>
        </label>
        <label>
          Estado
          <select
            value={recordForm.status}
            onChange={(event) => onUpdateRecordForm({ status: event.target.value })}
          >
            {recordStatusOptions.map((statusValue) => (
              <option key={statusValue} value={statusValue}>
                {statusValue}
              </option>
            ))}
          </select>
        </label>
        <label>
          Fecha de referencia
          <input
            type="date"
            value={recordForm.date}
            onChange={(event) => onUpdateRecordForm({ date: event.target.value })}
          />
        </label>
        <label>
          Impuesto aplicado (0-1)
          <input
            type="number"
            min={0}
            max={1}
            step="0.01"
            value={recordForm.taxRate}
            onChange={(event) => onUpdateRecordForm({ taxRate: Number(event.target.value) })}
          />
        </label>

        <div className="table-responsive form-span">
          <table>
            <thead>
              <tr>
                <th>Producto</th>
                <th>Cantidad</th>
                <th>Costo unitario</th>
                <th>Subtotal</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {recordItems.map((item, index) => (
                <tr key={item.tempId}>
                  <td>
                    <select
                      value={item.productId ?? ""}
                      onChange={(event) =>
                        onUpdateRecordItem(index, {
                          productId: event.target.value ? Number(event.target.value) : null,
                        })
                      }
                    >
                      <option value="">Selecciona un producto</option>
                      {devices.map((device) => (
                        <option key={device.id} value={device.id}>
                          {device.sku} · {device.name}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      type="number"
                      min={1}
                      value={item.quantity}
                      onChange={(event) =>
                        onUpdateRecordItem(index, {
                          quantity: Number(event.target.value),
                        })
                      }
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      min={0}
                      step="0.01"
                      value={item.unitCost}
                      onChange={(event) =>
                        onUpdateRecordItem(index, {
                          unitCost: Number(event.target.value),
                        })
                      }
                    />
                  </td>
                  <td>
                    {currencyFormatter.format(
                      Math.max(0, item.quantity) * Math.max(0, item.unitCost),
                    )}
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn--ghost"
                      onClick={() => onRemoveRecordItem(index)}
                      disabled={recordItems.length === 1}
                    >
                      Quitar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="form-actions form-span">
          <div className="actions-row">
            <button type="button" className="btn btn--secondary" onClick={onAddRecordItem}>
              Agregar producto
            </button>
          </div>
          <div className="totals-card">
            <span>
              <strong>Subtotal:</strong> {currencyFormatter.format(recordSubtotal)}
            </span>
            <span>
              <strong>Impuestos:</strong> {currencyFormatter.format(recordTax)}
            </span>
            <span>
              <strong>Total:</strong> {currencyFormatter.format(recordTotal)}
            </span>
          </div>
        </div>
        <button type="submit" className="btn btn--primary form-span">
          Registrar compra
        </button>
      </form>
    </section>
  );
};

export default PurchasesFormModal;
