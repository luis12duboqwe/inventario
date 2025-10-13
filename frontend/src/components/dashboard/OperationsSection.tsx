import Purchases from "../Purchases";
import Returns from "../Returns";
import Sales from "../Sales";
import TransferOrders from "../TransferOrders";
import POSDashboard from "../POS/POSDashboard";
import { useDashboard } from "./DashboardContext";

function OperationsSection() {
  const {
    token,
    stores,
    selectedStoreId,
    enablePurchasesSales,
    enableTransfers,
    refreshInventoryAfterTransfer,
  } = useDashboard();

  return (
    <div className="section-grid">
      {enablePurchasesSales ? (
        <>
          <Purchases
            token={token}
            stores={stores}
            defaultStoreId={selectedStoreId}
            onInventoryRefresh={refreshInventoryAfterTransfer}
          />
          <POSDashboard
            token={token}
            stores={stores}
            defaultStoreId={selectedStoreId}
            onInventoryRefresh={refreshInventoryAfterTransfer}
          />
          <Sales
            token={token}
            stores={stores}
            defaultStoreId={selectedStoreId}
            onInventoryRefresh={refreshInventoryAfterTransfer}
          />
          <Returns
            token={token}
            stores={stores}
            defaultStoreId={selectedStoreId}
            onInventoryRefresh={refreshInventoryAfterTransfer}
          />
        </>
      ) : (
        <section className="card">
          <h2>Compras y ventas</h2>
          <p className="muted-text">
            Activa el flag corporativo <code>SOFTMOBILE_ENABLE_PURCHASES_SALES</code> para operar compras, ventas y devoluciones.
          </p>
        </section>
      )}

      {enableTransfers ? (
        <TransferOrders
          token={token}
          stores={stores}
          defaultOriginId={selectedStoreId}
          onRefreshInventory={refreshInventoryAfterTransfer}
        />
      ) : (
        <section className="card">
          <h2>Transferencias entre tiendas</h2>
          <p className="muted-text">
            Para habilitar transferencias activa el flag <code>SOFTMOBILE_ENABLE_TRANSFERS</code>.
          </p>
        </section>
      )}
    </div>
  );
}

export default OperationsSection;

