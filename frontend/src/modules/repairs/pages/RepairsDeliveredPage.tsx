import PageHeader from "../../../components/layout/PageHeader";
import PageToolbar from "../../../components/layout/PageToolbar";
import RepairOrdersBoard from "./components/RepairOrdersBoard";
import { useRepairsLayout } from "./context/RepairsLayoutContext";

function RepairsDeliveredPage() {
  const { token, stores, selectedStoreId, setSelectedStoreId, setModuleStatus } = useRepairsLayout();

  return (
    <div className="repairs-subpage">
      <PageHeader
        title="Órdenes entregadas"
        subtitle="Consulta el historial de reparaciones entregadas y descarga comprobantes." // [PACK37-frontend]
      />

      <RepairOrdersBoard
        token={token}
        stores={stores}
        selectedStoreId={selectedStoreId}
        onSelectedStoreChange={setSelectedStoreId}
        onModuleStatusChange={setModuleStatus}
        initialStatusFilter="ENTREGADO"
        statusFilterOptions={["TODOS", "ENTREGADO", "LISTO", "CANCELADO"]} // [PACK37-frontend]
        renderToolbar={({ filters, actions }) => <PageToolbar actions={actions}>{filters}</PageToolbar>}
        showCreateForm={false}
      />
    </div>
  );
}

export default RepairsDeliveredPage;
