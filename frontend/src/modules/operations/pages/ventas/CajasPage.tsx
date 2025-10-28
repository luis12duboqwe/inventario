import { Suspense, lazy } from "react";

import Loader from "../../../../components/common/Loader";
import PageHeader from "../../../../components/layout/PageHeader";
import PageToolbar from "../../../../components/layout/PageToolbar";
import { useOperationsModule } from "../../hooks/useOperationsModule";

const OperationsHistoryPanel = lazy(() => import("../../components/OperationsHistoryPanel"));

function CajasPage() {
  const { token, stores } = useOperationsModule();

  return (
    <div className="operations-subpage">
      <PageHeader
        title="Cierres de caja"
        subtitle="Consulta aperturas, cierres y movimientos recientes por caja"
      />
      <PageToolbar />
      <Suspense fallback={<Loader message="Cargando historial de cajas…" />}>
        <OperationsHistoryPanel token={token} stores={stores} />
      </Suspense>
    </div>
  );
}

export default CajasPage;
