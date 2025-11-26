import PageHeader from "../../../components/layout/PageHeader";
import PageToolbar from "../../../components/layout/PageToolbar";
import RepairOrdersBoard from "./components/RepairOrdersBoard";
import { useRepairsLayout } from "./context/RepairsLayoutContext";

function RepairsFinalizedPage() {
  const { token, stores, selectedStoreId, setSelectedStoreId, setModuleStatus } = useRepairsLayout();

  return (
    <div className="repairs-subpage">
      <PageHeader
        title="Órdenes listas"
        subtitle="Revisa reparaciones listas para entrega y confirma pendientes con el cliente." // [PACK37-frontend]
      />

      <RepairOrdersBoard
        token={token}
        stores={stores}
        selectedStoreId={selectedStoreId}
        onSelectedStoreChange={setSelectedStoreId}
        onModuleStatusChange={setModuleStatus}
        initialStatusFilter="LISTO"
        statusFilterOptions={["TODOS", "LISTO", "EN_PROCESO", "ENTREGADO", "CANCELADO"]} // [PACK37-frontend]
        renderToolbar={({ filters, actions }) => <PageToolbar actions={actions} filters={filters} disableSearch />}
        showCreateForm={false}
      />
    </div>
  );
}

export default RepairsFinalizedPage;
