import Button from "@components/ui/Button";
import { useInventoryLayout } from "../context/InventoryLayoutContext";

function InventorySuppliersSection() {
  const {
    module: {
      supplierBatchOverview,
      supplierBatchLoading,
      refreshSupplierBatchOverview,
      selectedStore,
      formatCurrency,
    },
  } = useInventoryLayout();

  return (
    <section className="card wide">
      <header className="card-header">
        <div>
          <h2>Lotes recientes por proveedor</h2>
          <p className="card-subtitle">
            Seguimiento de compras asociadas a {selectedStore ? selectedStore.name : "cada sucursal"}.
          </p>
        </div>
        <div className="card-actions">
          <Button
            variant="ghost"
            size="sm"
            type="button"
            onClick={() => {
              void refreshSupplierBatchOverview();
            }}
            disabled={supplierBatchLoading}
          >
            {supplierBatchLoading ? "Actualizando…" : "Actualizar"}
          </Button>
        </div>
      </header>
      {supplierBatchLoading ? (
        <p className="muted-text">Cargando lotes recientes…</p>
      ) : supplierBatchOverview.length === 0 ? (
        <p className="muted-text">
          {selectedStore
            ? "Aún no se registran lotes para esta sucursal."
            : "Selecciona una sucursal para consultar sus lotes recientes."}
        </p>
      ) : (
        <ul className="metrics-list">
          {supplierBatchOverview.map((item) => (
            <li key={item.supplier_id}>
              <strong>{item.supplier_name}</strong> · {item.batch_count} lote{item.batch_count === 1 ? "" : "s"}
              <div>
                {item.total_quantity} unidades · {formatCurrency(item.total_value)}
              </div>
              <div className="muted-text">
                Último lote {item.latest_batch_code ?? "N/D"} — {new Date(item.latest_purchase_date).toLocaleDateString("es-HN")}
                {item.latest_unit_cost != null ? (
                  <span> · Costo unitario reciente: {formatCurrency(item.latest_unit_cost)}</span>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default InventorySuppliersSection;
