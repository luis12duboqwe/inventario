import PageHeader from "../../../components/layout/PageHeader";
import PageToolbar from "../../../components/layout/PageToolbar";
import type { PageHeaderAction } from "../../../components/layout/PageHeader";
import RepairOrdersBoard from "./components/RepairOrdersBoard";
import { useRepairsLayout } from "./context/RepairsLayoutContext";

function RepairsInProgressPage() {
  const {
    token,
    stores,
    selectedStoreId,
    setSelectedStoreId,
    onInventoryRefresh,
    setModuleStatus,
  } = useRepairsLayout();

  const headerActions: PageHeaderAction[] = onInventoryRefresh
    ? [
        {
          id: "refresh-inventory",
          label: "Actualizar inventario",
          onClick: () => {
            void onInventoryRefresh();
          },
          variant: "ghost",
        },
      ]
    : [];

  return (
    <div className="repairs-subpage">
      <PageHeader
        title="Órdenes en proceso"
        subtitle="Coordina las reparaciones que siguen activas y asigna responsables."
        actions={headerActions}
      />

      <RepairOrdersBoard
        token={token}
        stores={stores}
        selectedStoreId={selectedStoreId}
        onSelectedStoreChange={setSelectedStoreId}
        {...(onInventoryRefresh ? { onInventoryRefresh } : {})}
        onModuleStatusChange={setModuleStatus}
        initialStatusFilter="EN_PROCESO"
        statusFilterOptions={["TODOS", "EN_PROCESO", "PENDIENTE", "LISTO", "CANCELADO"]} // [PACK37-frontend]
        renderToolbar={({ filters, actions }) => <PageToolbar actions={actions} filters={filters} disableSearch />}
        showCreateForm={false}
      />
    </div>
  );
}

export default RepairsInProgressPage;
