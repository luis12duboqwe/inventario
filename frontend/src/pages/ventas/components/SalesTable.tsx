import type { Sale } from "../../../api";

const paymentLabels: Record<Sale["payment_method"], string> = {
  EFECTIVO: "Efectivo",
  TARJETA: "Tarjeta",
  TRANSFERENCIA: "Transferencia",
  OTRO: "Otro",
  CREDITO: "Crédito",
};

type Props = {
  sales: Sale[];
  isLoading: boolean;
  formatCurrency: (value: number) => string;
};

function SalesTable({ sales, isLoading, formatCurrency }: Props) {
  return (
    <div className="section-divider">
      {isLoading ? (
        <p className="muted-text">Cargando ventas registradas...</p>
      ) : sales.length === 0 ? (
        <p className="muted-text">No hay ventas que coincidan con los filtros seleccionados.</p>
      ) : (
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Fecha</th>
                <th>Sucursal</th>
                <th>Cliente</th>
                <th>Usuario</th>
                <th>Método</th>
                <th>Subtotal</th>
                <th>Impuesto</th>
                <th>Total</th>
                <th>Artículos</th>
              </tr>
            </thead>
            <tbody>
              {sales.map((sale) => (
                <tr key={sale.id}>
                  <td>#{sale.id}</td>
                  <td>{new Date(sale.created_at).toLocaleString("es-HN")}</td>
                  <td>{sale.store?.name ?? `Sucursal #${sale.store_id}`}</td>
                  <td>{sale.customer_name ?? "Mostrador"}</td>
                  <td>{sale.performed_by?.full_name ?? sale.performed_by?.username ?? "—"}</td>
                  <td>{paymentLabels[sale.payment_method]}</td>
                  <td>{formatCurrency(sale.subtotal_amount)}</td>
                  <td>{formatCurrency(sale.tax_amount)}</td>
                  <td>{formatCurrency(sale.total_amount)}</td>
                  <td>
                    <ul className="compact-list">
                      {sale.items.map((item) => (
                        <li key={item.id}>
                          {item.device?.sku ?? `ID ${item.device_id}`} · {item.quantity} uds — {formatCurrency(item.total_line)}
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
  );
}

export default SalesTable;
