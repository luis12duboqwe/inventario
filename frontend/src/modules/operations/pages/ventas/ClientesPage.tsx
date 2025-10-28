import { Suspense, lazy } from "react";

import Loader from "../../../../components/common/Loader";
import PageHeader from "../../../../components/layout/PageHeader";
import PageToolbar from "../../../../components/layout/PageToolbar";
import { useOperationsModule } from "../../hooks/useOperationsModule";

const CustomersPanel = lazy(() => import("../../components/Customers"));

function ClientesPage() {
  const { token } = useOperationsModule();

  return (
    <div className="operations-subpage">
      <PageHeader
        title="Clientes"
        subtitle="Administra cartera, notas internas y límites de crédito"
      />
      <PageToolbar />
      <Suspense fallback={<Loader message="Cargando clientes…" />}>
        <CustomersPanel token={token} />
      </Suspense>
    </div>
  );
}

export default ClientesPage;
