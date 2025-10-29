import type { FormEvent } from "react";
import type { Customer, Device, Sale, Store } from "../../../api";
import type { SaleFormState, SaleLine, SaleSummary } from "./types";

type Props = {
  stores: Store[];
  customers: Customer[];
  saleForm: SaleFormState;
  onSaleFormChange: (changes: Partial<SaleFormState>) => void;
  deviceQuery: string;
  onDeviceQueryChange: (value: string) => void;
  devices: Device[];
  isLoadingDevices: boolean;
  onAddDevice: (device: Device) => void;
  saleItems: SaleLine[];
  onQuantityChange: (deviceId: number, quantity: number) => void;
  onRemoveLine: (deviceId: number) => void;
  saleSummary: SaleSummary;
  paymentLabels: Record<Sale["payment_method"], string>;
  isSaving: boolean;
  isPrinting: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onReset: () => void;
  onRequestInvoice: () => void;
  formatCurrency: (value: number) => string;
  invoiceAvailable: boolean;
};

function SidePanel({
  stores,
  customers,
  saleForm,
  onSaleFormChange,
  deviceQuery,
  onDeviceQueryChange,
  devices,
  isLoadingDevices,
  onAddDevice,
  saleItems,
  onQuantityChange,
  onRemoveLine,
  saleSummary,
  paymentLabels,
  isSaving,
  isPrinting,
  onSubmit,
  onReset,
  onRequestInvoice,
  formatCurrency,
  invoiceAvailable,
}: Props) {
  const deviceSearchDisabled = !saleForm.storeId;

  return (
    <form className="sales-form" onSubmit={onSubmit}>
      <div className="form-grid">
        <label>
          Sucursal
          <select
            value={saleForm.storeId ?? ""}
            onChange={(event) =>
              onSaleFormChange({ storeId: event.target.value ? Number(event.target.value) : null })
            }
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
          Cliente registrado
          <select
            value={saleForm.customerId ?? ""}
            onChange={(event) =>
              onSaleFormChange({
                customerId: event.target.value ? Number(event.target.value) : null,
                customerName: "",
              })
            }
          >
            <option value="">Venta de mostrador</option>
            {customers.map((customer) => (
              <option key={customer.id} value={customer.id}>
                {customer.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Cliente manual (opcional)
          <input
            value={saleForm.customerName}
            onChange={(event) => onSaleFormChange({ customerName: event.target.value, customerId: null })}
            placeholder="Nombre del cliente"
          />
        </label>

        <label>
          Método de pago
          <select
            value={saleForm.paymentMethod}
            onChange={(event) =>
              onSaleFormChange({ paymentMethod: event.target.value as Sale["payment_method"] })
            }
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
            value={saleForm.discountPercent}
            onChange={(event) => onSaleFormChange({ discountPercent: Number(event.target.value) })}
          />
        </label>

        <label>
          Nota interna
          <input
            value={saleForm.notes}
            onChange={(event) => onSaleFormChange({ notes: event.target.value })}
            placeholder="Observaciones"
          />
        </label>

        <label>
          Motivo corporativo
          <input
            value={saleForm.reason}
            onChange={(event) => onSaleFormChange({ reason: event.target.value })}
            placeholder="Motivo para auditoría"
          />
        </label>

        <label className="span-2">
          Buscar dispositivo por IMEI, SKU o modelo
          <input
            value={deviceQuery}
            onChange={(event) => onDeviceQueryChange(event.target.value)}
            placeholder="Ej. 990000862471854 o FILTRO-1001"
            disabled={deviceSearchDisabled}
          />
        </label>
      </div>

      <div className="section-divider">
        <h3>Dispositivos disponibles</h3>
        {!saleForm.storeId ? (
          <p className="muted-text">Selecciona una sucursal para consultar su inventario disponible.</p>
        ) : isLoadingDevices ? (
          <p className="muted-text">Cargando dispositivos disponibles...</p>
        ) : devices.length === 0 ? (
          <p className="muted-text">No se encontraron dispositivos disponibles con el criterio indicado.</p>
        ) : (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Modelo</th>
                  <th>Estado</th>
                  <th>Precio</th>
                  <th>Disponibles</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {devices.map((device) => (
                  <tr key={device.id}>
                    <td>{device.sku}</td>
                    <td>{device.name}</td>
                    <td>{device.condition_label ?? device.condition}</td>
                    <td>{formatCurrency(device.unit_price)}</td>
                    <td>{device.quantity}</td>
                    <td>
                      <button
                        type="button"
                        className="btn btn--secondary"
                        onClick={() => onAddDevice(device)}
                        disabled={device.quantity === 0}
                      >
                        Agregar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="section-divider">
        <h3>Carrito de venta</h3>
        {saleItems.length === 0 ? (
          <p className="muted-text">Agrega dispositivos para calcular el total de la venta.</p>
        ) : (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Descripción</th>
                  <th>Cantidad</th>
                  <th>Precio unitario</th>
                  <th>Total línea</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {saleItems.map((line) => (
                  <tr key={line.device.id}>
                    <td>{line.device.sku}</td>
                    <td>{line.device.name}</td>
                    <td>
                      <input
                        type="number"
                        min={1}
                        max={line.device.quantity}
                        value={line.quantity}
                        onChange={(event) =>
                          onQuantityChange(line.device.id, Number(event.target.value))
                        }
                      />
                    </td>
                    <td>{formatCurrency(line.device.unit_price)}</td>
                    <td>{formatCurrency(line.device.unit_price * line.quantity)}</td>
                    <td>
                      <button
                        type="button"
                        className="btn btn--ghost"
                        onClick={() => onRemoveLine(line.device.id)}
                      >
                        Quitar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="totals-grid">
          <div className="totals-card">
            <h4>Resumen</h4>
            <ul className="compact-list">
              <li>Total bruto: {formatCurrency(saleSummary.gross)}</li>
              <li>Descuento: {formatCurrency(saleSummary.discount)}</li>
              <li>Subtotal: {formatCurrency(saleSummary.subtotal)}</li>
              <li>
                Impuesto ({saleSummary.taxRate.toFixed(2)}%): {formatCurrency(saleSummary.taxAmount)}
              </li>
              <li className="highlight">Total a cobrar: {formatCurrency(saleSummary.total)}</li>
            </ul>
          </div>
          <div className="actions-card">
            <button type="submit" className="btn btn--primary" disabled={isSaving}>
              {isSaving ? "Guardando..." : "Guardar venta"}
            </button>
            <button
              type="button"
              className="btn btn--secondary"
              onClick={onRequestInvoice}
              disabled={!invoiceAvailable || isPrinting}
            >
              {isPrinting ? "Generando factura..." : "Imprimir factura"}
            </button>
            <button type="button" className="btn btn--ghost" onClick={onReset}>
              Limpiar formulario
            </button>
          </div>
        </div>
      </div>
    </form>
  );
}

export default SidePanel;
