import { Suspense, lazy } from "react";

import Loader from "../../../../components/common/Loader";
import PageHeader from "../../../../components/layout/PageHeader";
import PageToolbar from "../../../../components/layout/PageToolbar";
import { useOperationsModule } from "../../hooks/useOperationsModule";

const SalesPanel = lazy(() => import("../../components/Sales"));
const ReturnsPanel = lazy(() => import("../../components/Returns"));

function FacturacionPage() {
  const { token, stores, selectedStoreId, enablePurchasesSales, refreshInventoryAfterTransfer } =
    useOperationsModule();

  if (!enablePurchasesSales) {
    return (
      <div className="operations-subpage">
        <PageHeader
          title="Facturación"
          subtitle="Genera facturas, notas de venta y devoluciones con motivo corporativo"
        />
        <section className="card">
          <p className="muted-text">
            Activa el flag corporativo <code>SOFTMOBILE_ENABLE_PURCHASES_SALES</code> para utilizar facturación y devoluciones.
          </p>
        </section>
      </div>
    );
  }

  return (
    <div className="operations-subpage">
      <PageHeader
        title="Facturación"
        subtitle="Controla ventas, devoluciones y notas fiscales sincronizadas"
      />
      <PageToolbar />
      <div className="operations-subpage__grid">
        <Suspense fallback={<Loader message="Cargando ventas…" />}>
          <SalesPanel
            token={token}
            stores={stores}
            defaultStoreId={selectedStoreId}
            onInventoryRefresh={refreshInventoryAfterTransfer}
          />
        </Suspense>
        <Suspense fallback={<Loader message="Cargando devoluciones…" />}>
          <ReturnsPanel
            token={token}
            stores={stores}
            defaultStoreId={selectedStoreId}
            onInventoryRefresh={refreshInventoryAfterTransfer}
          />
        </Suspense>
      </div>
    </div>
  );
}

export default FacturacionPage;
