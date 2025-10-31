// [PACK29-*] Tabla de productos con mejor desempeño
import ScrollableTable from "@/shared/components/ScrollableTable";
import type { SalesByProductItem } from "@/services/api/reports";

export type TopProductsTableProps = {
  products?: SalesByProductItem[];
  isLoading?: boolean;
  formatCurrency: (value: number) => string;
};

function TopProductsTable({ products, isLoading = false, formatCurrency }: TopProductsTableProps) {
  return (
    <section className="card reports-card section-scroll" aria-label="Top productos vendidos">
      <div className="reports-card__header">
        <div>
          <h2>Top productos</h2>
          <p className="muted-text">Detalle por SKU con montos brutos y netos.</p>
        </div>
      </div>
      {isLoading ? (
        <div className="loading-overlay compact" role="status" aria-live="polite">
          <span className="spinner" aria-hidden="true" />
          <span>Consultando productos destacados…</span>
        </div>
      ) : products && products.length > 0 ? (
        <ScrollableTable>
          <table>
            <thead>
              <tr>
                <th scope="col">SKU</th>
                <th scope="col">Producto</th>
                <th scope="col">Cantidad</th>
                <th scope="col">Ventas brutas</th>
                <th scope="col">Ventas netas</th>
              </tr>
            </thead>
            <tbody>
              {products.map((item) => (
                <tr key={item.sku}>
                  <td>{item.sku}</td>
                  <td>{item.name}</td>
                  <td>{item.qty}</td>
                  <td>{formatCurrency(item.gross)}</td>
                  <td>{formatCurrency(item.net)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollableTable>
      ) : (
        <p className="muted-text">No se registraron productos en el periodo seleccionado.</p>
      )}
    </section>
  );
}

export default TopProductsTable;
