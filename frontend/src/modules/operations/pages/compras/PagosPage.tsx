import { Suspense, lazy } from "react";

import Loader from "../../../../components/common/Loader";
import PageHeader from "../../../../components/layout/PageHeader";
import PageToolbar from "../../../../components/layout/PageToolbar";
import { useOperationsModule } from "../../hooks/useOperationsModule";

const PurchasesPanel = lazy(() => import("../../components/Purchases"));

function PagosPage() {
  const { token, stores, selectedStoreId, enablePurchasesSales, refreshInventoryAfterTransfer } =
    useOperationsModule();

  if (!enablePurchasesSales) {
    return (
      <div className="operations-subpage">
        <PageHeader
          title="Pagos a proveedores"
          subtitle="Registra desembolsos, notas de crédito y devoluciones"
        />
        <section className="card">
          <p className="muted-text">
            Activa el flag corporativo <code>SOFTMOBILE_ENABLE_PURCHASES_SALES</code> para administrar pagos a proveedores.
          </p>
        </section>
      </div>
    );
  }

  return (
    <div className="operations-subpage">
      <PageHeader
        title="Pagos a proveedores"
        subtitle="Controla facturas, notas de crédito y saldos con tus proveedores"
      />
      <PageToolbar />
      <Suspense fallback={<Loader message="Cargando pagos…" />}>
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

export default PagosPage;
