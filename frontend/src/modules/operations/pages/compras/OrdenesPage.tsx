import { Suspense, lazy } from "react";

import Loader from "../../../../components/common/Loader";
import PageHeader from "../../../../components/layout/PageHeader";
import PageToolbar from "../../../../components/layout/PageToolbar";
import { useOperationsModule } from "../../hooks/useOperationsModule";

const PurchasesPanel = lazy(() => import("../../components/Purchases"));

function OrdenesPage() {
  const { token, stores, selectedStoreId, enablePurchasesSales, refreshInventoryAfterTransfer } =
    useOperationsModule();

  if (!enablePurchasesSales) {
    return (
      <div className="operations-subpage">
        <PageHeader
          title="Órdenes de compra"
          subtitle="Registra recepciones parciales y controla el costo promedio"
        />
        <section className="card">
          <p className="muted-text">
            Activa el flag corporativo <code>SOFTMOBILE_ENABLE_PURCHASES_SALES</code> para gestionar órdenes de compra.
          </p>
        </section>
      </div>
    );
  }

  return (
    <div className="operations-subpage">
      <PageHeader
        title="Órdenes de compra"
        subtitle="Crea órdenes, registra recepciones y sincroniza inventario"
      />
      <PageToolbar />
      <Suspense fallback={<Loader message="Cargando órdenes de compra…" />}>
        <PurchasesPanel
          token={token}
          stores={stores}
          defaultStoreId={selectedStoreId}
          onInventoryRefresh={refreshInventoryAfterTransfer}
        />
      </Suspense>
    </div>
  );
}

export default OrdenesPage;
