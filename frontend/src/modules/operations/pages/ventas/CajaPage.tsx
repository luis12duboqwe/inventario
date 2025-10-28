import { Suspense, lazy } from "react";

import Loader from "../../../../components/common/Loader";
import PageHeader from "../../../../components/layout/PageHeader";
import PageToolbar from "../../../../components/layout/PageToolbar";
import { useOperationsModule } from "../../hooks/useOperationsModule";

const POSDashboard = lazy(() => import("../../components/POS/POSDashboard"));

function CajaPage() {
  const { token, stores, selectedStoreId, enablePurchasesSales, refreshInventoryAfterTransfer } =
    useOperationsModule();

  if (!enablePurchasesSales) {
    return (
      <div className="operations-subpage">
        <PageHeader
          title="Caja y POS"
          subtitle="Gestiona sesiones de caja, ventas rápidas y conciliaciones en tiempo real"
        />
        <section className="card">
          <p className="muted-text">
            Activa el flag corporativo <code>SOFTMOBILE_ENABLE_PURCHASES_SALES</code> para operar el punto de venta.
          </p>
        </section>
      </div>
    );
  }

  return (
    <div className="operations-subpage">
      <PageHeader
        title="Caja y POS"
        subtitle="Gestiona sesiones de caja, ventas rápidas y conciliaciones en tiempo real"
      />
      <PageToolbar />
      <Suspense fallback={<Loader message="Cargando panel de caja…" />}>
        <POSDashboard
          token={token}
          stores={stores}
          defaultStoreId={selectedStoreId}
          onInventoryRefresh={refreshInventoryAfterTransfer}
        />
      </Suspense>
    </div>
  );
}

export default CajaPage;
