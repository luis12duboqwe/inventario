import Purchases from "../components/Purchases";
import Returns from "../components/Returns";
import Sales from "../components/Sales";
import TransferOrders from "../components/TransferOrders";
import POSDashboard from "../components/POS/POSDashboard";
import Customers from "../components/Customers";
import Suppliers from "../components/Suppliers";
import { useOperationsModule } from "../hooks/useOperationsModule";

function OperationsPage() {
  const {
    token,
    stores,
    selectedStoreId,
    enablePurchasesSales,
    enableTransfers,
    refreshInventoryAfterTransfer,
  } = useOperationsModule();

  return (
    <div className="section-grid">
      {enablePurchasesSales ? (
        <>
          <Customers token={token} />
          <Suppliers token={token} />
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

export default OperationsPage;

