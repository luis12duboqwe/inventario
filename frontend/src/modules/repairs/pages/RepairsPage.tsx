import RepairOrders from "../components/RepairOrders";
import { useRepairsModule } from "../hooks/useRepairsModule";

function RepairsPage() {
  const { token, stores, selectedStoreId, refreshInventoryAfterTransfer, enablePurchasesSales } = useRepairsModule();

  if (!enablePurchasesSales) {
    return (
      <section className="card">
        <h2>Órdenes de reparación</h2>
        <p className="muted-text">
          Activa <code>SOFTMOBILE_ENABLE_PURCHASES_SALES</code> para habilitar el flujo de reparaciones y sus ajustes de
          inventario vinculados.
        </p>
      </section>
    );
  }

  return (
    <div className="section-grid">
      <RepairOrders
        token={token}
        stores={stores}
        defaultStoreId={selectedStoreId}
        onInventoryRefresh={refreshInventoryAfterTransfer}
      />
    </div>
  );
}

export default RepairsPage;
