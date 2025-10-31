import { Suspense, lazy } from "react";

import Loader from "../../../../components/common/Loader";
import PageHeader from "../../../../components/layout/PageHeader";
import PageToolbar from "../../../../components/layout/PageToolbar";
import { useOperationsModule } from "../../hooks/useOperationsModule";

const InternalMovementsPanel = lazy(() => import("../../components/InternalMovementsPanel"));

function MovimientosInternosPage() {
  const { stores, selectedStoreId } = useOperationsModule();

  return (
    <div className="operations-subpage">
      <PageHeader
        title="Movimientos internos"
        subtitle="Ajustes, recepciones y conteos con motivo corporativo obligatorio"
      />
      <PageToolbar />
      <Suspense fallback={<Loader message="Cargando movimientos internos…" />}>
        <InternalMovementsPanel stores={stores} defaultStoreId={selectedStoreId} />
      </Suspense>
    </div>
  );
}

export default MovimientosInternosPage;
