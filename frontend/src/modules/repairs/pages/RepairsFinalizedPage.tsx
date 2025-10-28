import PageHeader from "../../../components/layout/PageHeader";
import PageToolbar from "../../../components/layout/PageToolbar";
import RepairOrdersBoard from "./components/RepairOrdersBoard";
import { useRepairsLayout } from "./context/RepairsLayoutContext";

function RepairsFinalizedPage() {
  const { token, stores, selectedStoreId, setSelectedStoreId, setModuleStatus } = useRepairsLayout();

  return (
    <div className="repairs-subpage">
      <PageHeader
        title="Órdenes finalizadas"
        subtitle="Consulta las reparaciones listas o entregadas y descarga sus comprobantes."
      />

      <RepairOrdersBoard
        token={token}
        stores={stores}
        selectedStoreId={selectedStoreId}
        onSelectedStoreChange={setSelectedStoreId}
        onModuleStatusChange={setModuleStatus}
        initialStatusFilter="LISTO"
        statusFilterOptions={["TODOS", "LISTO", "ENTREGADO"]}
        renderToolbar={({ filters, actions }) => <PageToolbar actions={actions}>{filters}</PageToolbar>}
        showCreateForm={false}
      />
    </div>
  );
}

export default RepairsFinalizedPage;
