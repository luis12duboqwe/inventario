import PageHeader from "../../../components/layout/PageHeader";
import PageToolbar from "../../../components/layout/PageToolbar";
import type { PageHeaderAction } from "../../../components/layout/PageHeader";
import RepairOrdersBoard from "./components/RepairOrdersBoard";
import { useRepairsLayout } from "./context/RepairsLayoutContext";

function RepairsPendingPage() {
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
        title="Órdenes pendientes"
        subtitle="Gestiona nuevas reparaciones y controla las que siguen en proceso."
        actions={headerActions}
      />

      <RepairOrdersBoard
        token={token}
        stores={stores}
        selectedStoreId={selectedStoreId}
        onSelectedStoreChange={setSelectedStoreId}
        {...(onInventoryRefresh ? { onInventoryRefresh } : {})}
        onModuleStatusChange={setModuleStatus}
        initialStatusFilter="PENDIENTE"
        renderToolbar={({ filters, actions }) => <PageToolbar actions={actions} filters={filters} disableSearch />}
        showCreateForm
      />
    </div>
  );
}

export default RepairsPendingPage;
