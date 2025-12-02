import type { SaleLine } from "./types";

type Props = {
  saleItems: SaleLine[];
  onQuantityChange: (deviceId: number, quantity: number) => void;
  onBatchCodeChange: (deviceId: number, batchCode: string) => void;
  onRemoveLine: (deviceId: number) => void;
  formatCurrency: (value: number) => string;
};

export function SaleCart({
  saleItems,
  onQuantityChange,
  onBatchCodeChange,
  onRemoveLine,
  formatCurrency,
}: Props) {
  return (
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
                <th>Lote</th>
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
                  <td>
                    <input
                      value={line.batchCode}
                      onChange={(event) => onBatchCodeChange(line.device.id, event.target.value)}
                      placeholder="Ej. L-2024-01"
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
    </div>
  );
}
