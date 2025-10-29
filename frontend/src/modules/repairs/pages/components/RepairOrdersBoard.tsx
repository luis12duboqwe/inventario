import { useMemo, useState, type ReactNode } from "react";

import type { RepairOrder, Store } from "../../../../api";
import type { ModuleStatus } from "../../../../shared/components/ModuleHeader";
import type { PageHeaderAction } from "../../../../components/layout/PageHeader";

import BudgetModal from "../../../../pages/reparaciones/components/BudgetModal";
import FiltersPanel from "../../../../pages/reparaciones/components/FiltersPanel";
import PartsModal from "../../../../pages/reparaciones/components/PartsModal";
import RepairTable from "../../../../pages/reparaciones/components/RepairTable";
import SidePanel from "../../../../pages/reparaciones/components/SidePanel";
import Toolbar from "../../../../pages/reparaciones/components/Toolbar";
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
  const [selectedBudgetOrder, setSelectedBudgetOrder] = useState<RepairOrder | null>(null);
  const [selectedPartsOrder, setSelectedPartsOrder] = useState<RepairOrder | null>(null);

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
    onShowBudget: (order) => setSelectedBudgetOrder(order),
    onShowParts: (order) => setSelectedPartsOrder(order),
  });

  const deviceLabelById = useMemo(() => {
    const mapping = new Map<number, string>();
    devices.forEach((device) => {
      const label = device.sku ? `${device.sku} · ${device.name}` : device.name;
      mapping.set(device.id, label);
    });
    return mapping;
  }, [devices]);

  const resolveDeviceLabel = (deviceId: number) => deviceLabelById.get(deviceId) ?? `Dispositivo #${deviceId}`;

  const filtersSection = (
    <FiltersPanel
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

  const defaultToolbar = <Toolbar actions={toolbarActions}>{filtersSection}</Toolbar>;

  const toolbar = renderToolbar ? renderToolbar({ filters: filtersSection, actions: toolbarActions }) : defaultToolbar;

  return (
    <section className="card wide">
      <h2>Órdenes de reparación</h2>
      <p className="card-subtitle">
        Gestiona reparaciones con control de piezas, técnicos, estados y descarga inmediata de órdenes en PDF.
      </p>
      {message ? <div className="alert success">{message}</div> : null}
      {error ? <div className="alert error">{error}</div> : null}

      {showCreateFormEnabled ? (
        <SidePanel
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

      <RepairTable
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

      <BudgetModal
        order={selectedBudgetOrder}
        open={selectedBudgetOrder !== null}
        onClose={() => setSelectedBudgetOrder(null)}
      />

      <PartsModal
        order={selectedPartsOrder}
        open={selectedPartsOrder !== null}
        onClose={() => setSelectedPartsOrder(null)}
        resolveDeviceLabel={resolveDeviceLabel}
      />
    </section>
  );
}

export type { RepairOrdersBoardProps };
export default RepairOrdersBoard;
