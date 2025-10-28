import type { ReactNode } from "react";

import type { RepairOrder, Store } from "../../../../api";
import type { ModuleStatus } from "../../../../shared/components/ModuleHeader";
import type { PageHeaderAction } from "../../../../components/layout/PageHeader";

import RepairOrderFormSection from "./RepairOrderFormSection";
import RepairOrdersFiltersSection from "./RepairOrdersFiltersSection";
import RepairOrdersTableSection from "./RepairOrdersTableSection";
import useRepairOrdersBoard from "./useRepairOrdersBoard";

type RepairOrdersBoardProps = {
  token: string;
  stores: Store[];
  selectedStoreId: number | null;
  onSelectedStoreChange: (storeId: number | null) => void;
  onInventoryRefresh?: () => void;
  onModuleStatusChange?: (status: ModuleStatus, label: string) => void;
  initialStatusFilter?: RepairOrder["status"] | "TODOS";
  statusFilterOptions?: Array<RepairOrder["status"] | "TODOS">;
  showCreateForm?: boolean;
  renderToolbar?: (payload: { filters: ReactNode; actions: PageHeaderAction[] }) => ReactNode;
  searchPlaceholder?: string;
};

function RepairOrdersBoard({
  token,
  stores,
  selectedStoreId,
  onSelectedStoreChange,
  onInventoryRefresh,
  onModuleStatusChange,
  initialStatusFilter = "TODOS",
  statusFilterOptions,
  showCreateForm = true,
  renderToolbar,
  searchPlaceholder,
}: RepairOrdersBoardProps) {
  const {
    localStoreId,
    handleStoreChange,
    message,
    error,
    loading,
    orders,
    form,
    updateForm,
    updatePart,
    addPart,
    removePart,
    resetForm,
    customers,
    customerSearch,
    setCustomerSearch,
    devices,
    handleCreate,
    handleExportCsv,
    renderRepairRow,
    statusFilter,
    handleStatusFilterChange,
    availableStatusFilters,
    getStatusLabel,
    search,
    handleSearchChange,
    showCreateForm: showCreateFormEnabled,
  } = useRepairOrdersBoard({
    token,
    selectedStoreId,
    onSelectedStoreChange,
    onInventoryRefresh,
    onModuleStatusChange,
    initialStatusFilter,
    statusFilterOptions,
    showCreateForm,
  });

  const filtersSection = (
    <RepairOrdersFiltersSection
      statusFilter={statusFilter}
      statusOptions={availableStatusFilters}
      onStatusFilterChange={handleStatusFilterChange}
      search={search}
      onSearchChange={handleSearchChange}
      searchPlaceholder={searchPlaceholder}
      totalOrders={orders.length}
      getStatusLabel={getStatusLabel}
    />
  );

  const toolbarActions: PageHeaderAction[] = [
    {
      id: "export-repairs",
      label: "Exportar CSV",
      onClick: handleExportCsv,
      variant: "ghost",
    },
  ];

  const toolbar = renderToolbar ? renderToolbar({ filters: filtersSection, actions: toolbarActions }) : filtersSection;

  return (
    <section className="card wide">
      <h2>Órdenes de reparación</h2>
      <p className="card-subtitle">
        Gestiona reparaciones con control de piezas, técnicos, estados y descarga inmediata de órdenes en PDF.
      </p>
      {message ? <div className="alert success">{message}</div> : null}
      {error ? <div className="alert error">{error}</div> : null}

      {showCreateFormEnabled ? (
        <RepairOrderFormSection
          stores={stores}
          selectedStoreId={localStoreId}
          form={form}
          customers={customers}
          devices={devices}
          customerSearch={customerSearch}
          onCustomerSearchChange={setCustomerSearch}
          onStoreChange={handleStoreChange}
          onFormChange={updateForm}
          onSubmit={handleCreate}
          onReset={resetForm}
          onAddPart={addPart}
          onRemovePart={removePart}
          onPartChange={updatePart}
        />
      ) : null}

      {toolbar}

      <RepairOrdersTableSection
        loading={loading}
        orders={orders}
        renderHead={() => (
          <>
            <th scope="col">Folio</th>
            <th scope="col">Cliente</th>
            <th scope="col">Técnico</th>
            <th scope="col">Diagnóstico</th>
            <th scope="col">Estado</th>
            <th scope="col">Total</th>
            <th scope="col">Actualizado</th>
            <th scope="col">Inventario</th>
            <th scope="col">Acciones</th>
          </>
        )}
        renderRow={renderRepairRow}
      />
    </section>
  );
}

export type { RepairOrdersBoardProps };
export default RepairOrdersBoard;
