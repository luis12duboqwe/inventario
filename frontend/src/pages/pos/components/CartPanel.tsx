import type { Device } from "../../../api";

type CartLine = {
  device: Device;
  quantity: number;
  discountPercent: number;
};

type Totals = {
  subtotal: number;
  tax: number;
  total: number;
};

type Props = {
  items: CartLine[];
  onUpdate: (deviceId: number, updates: Partial<CartLine>) => void;
  onRemove: (deviceId: number) => void;
  totals: Totals;
  hasTaxes: boolean;
  globalDiscount: number;
};

function CartPanel({ items, onUpdate, onRemove, totals, hasTaxes, globalDiscount }: Props) {
  const formatCurrency = (value: number) => value.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  return (
    <section className="card">
      <h3>Carrito</h3>
      <p className="card-subtitle">Gestiona cantidades, descuentos y elimina productos antes de cobrar.</p>
      {items.length === 0 ? (
        <p className="muted-text">Escanea un IMEI o selecciona un dispositivo para comenzar.</p>
      ) : (
        <div className="table-container">
          <table className="responsive-table">
            <thead>
              <tr>
                <th>Producto</th>
                <th className="numeric">Stock</th>
                <th className="numeric">Cantidad</th>
                <th className="numeric">Desc. %</th>
                <th className="numeric">Total</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((line) => {
                const available = line.device.quantity;
                const hasWarning = line.quantity > available;
                const unitPrice = line.device.unit_price ?? 0;
                const appliedDiscount = line.discountPercent > 0 ? line.discountPercent : globalDiscount;
                const lineBase = unitPrice * line.quantity;
                const discountAmount = lineBase * (appliedDiscount / 100);
                const lineTotal = lineBase - discountAmount;
                return (
                  <tr key={line.device.id} className={hasWarning ? "warning-row" : undefined}>
                    <td>
                      <strong>{line.device.name}</strong>
                      <br />
                      <span className="muted-text">SKU {line.device.sku}</span>
                      {hasWarning ? (
                        <div className="alert warning inline">Quedan {available} unidades en inventario.</div>
                      ) : null}
                    </td>
                    <td className="numeric">{available}</td>
                    <td className="numeric">
                      <input
                        type="number"
                        min={1}
                        value={line.quantity}
                        onChange={(event) =>
                          onUpdate(line.device.id, { quantity: Math.max(1, Number(event.target.value)) })
                        }
                      />
                    </td>
                    <td className="numeric">
                      <input
                        type="number"
                        min={0}
                        max={100}
                        value={line.discountPercent}
                        onChange={(event) =>
                          onUpdate(line.device.id, {
                            discountPercent: Math.min(100, Math.max(0, Number(event.target.value))),
                          })
                        }
                      />
                    </td>
                    <td className="numeric">${formatCurrency(lineTotal)}</td>
                    <td className="numeric">
                      <button type="button" className="btn btn--ghost" onClick={() => onRemove(line.device.id)}>
                        Quitar
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={4} className="numeric">Subtotal</td>
                <td className="numeric">${formatCurrency(totals.subtotal)}</td>
                <td></td>
              </tr>
              <tr>
                <td colSpan={4} className="numeric">Impuestos {hasTaxes ? "incluidos" : "omitidos"}</td>
                <td className="numeric">${formatCurrency(totals.tax)}</td>
                <td></td>
              </tr>
              <tr>
                <td colSpan={4} className="numeric total-row">Total</td>
                <td className="numeric total-row">${formatCurrency(totals.total)}</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </section>
  );
}

export type { CartLine };
export default CartPanel;
