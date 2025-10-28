import { Suspense, lazy } from "react";

import Loader from "../../../../components/common/Loader";
import PageHeader from "../../../../components/layout/PageHeader";
import PageToolbar from "../../../../components/layout/PageToolbar";
import { useOperationsModule } from "../../hooks/useOperationsModule";

const SuppliersPanel = lazy(() => import("../../components/Suppliers"));

function ProveedoresPage() {
  const { token, stores } = useOperationsModule();

  return (
    <div className="operations-subpage">
      <PageHeader
        title="Proveedores"
        subtitle="Gestiona catálogos, lotes y saldos pendientes"
      />
      <PageToolbar />
      <Suspense fallback={<Loader message="Cargando proveedores…" />}>
        <SuppliersPanel token={token} stores={stores} />
      </Suspense>
    </div>
  );
}

export default ProveedoresPage;
