import { Suspense, lazy } from "react";

import Loader from "../../../../components/common/Loader";
import PageHeader from "../../../../components/layout/PageHeader";
import PageToolbar from "../../../../components/layout/PageToolbar";
import { useOperationsModule } from "../../hooks/useOperationsModule";

const TransferOrdersPanel = lazy(() => import("../../components/TransferOrders"));

function TransferenciasPage() {
  const { token, stores, selectedStoreId, enableTransfers, refreshInventoryAfterTransfer } =
    useOperationsModule();

  if (!enableTransfers) {
    return (
      <div className="operations-subpage">
        <PageHeader
          title="Transferencias entre tiendas"
          subtitle="Coordina envíos SOLICITADA → EN_TRANSITO → RECIBIDA"
        />
        <section className="card">
          <p className="muted-text">
            Activa el flag corporativo <code>SOFTMOBILE_ENABLE_TRANSFERS</code> para utilizar transferencias entre sucursales.
          </p>
        </section>
      </div>
    );
  }

  return (
    <div className="operations-subpage">
      <PageHeader
        title="Transferencias entre tiendas"
        subtitle="Solicita, despacha y recibe inventario sin salir del módulo"
      />
      <PageToolbar />
      <Suspense fallback={<Loader message="Cargando transferencias…" />}>
        <TransferOrdersPanel
          token={token}
          stores={stores}
          defaultOriginId={selectedStoreId}
          onRefreshInventory={refreshInventoryAfterTransfer}
        />
      </Suspense>
    </div>
  );
}

export default TransferenciasPage;
