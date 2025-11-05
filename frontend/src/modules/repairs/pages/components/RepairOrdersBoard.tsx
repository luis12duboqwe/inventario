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

  const hookOptions = {
    token,
    selectedStoreId,
    onSelectedStoreChange,
    initialStatusFilter,
    showCreateForm,
    onShowBudget: (order: RepairOrder) => setSelectedBudgetOrder(order),
    onShowParts: (order: RepairOrder) => setSelectedPartsOrder(order),
    ...(onInventoryRefresh ? { onInventoryRefresh } : {}),
    ...(onModuleStatusChange ? { onModuleStatusChange } : {}),
    ...(statusFilterOptions ? { statusFilterOptions } : {}),
  } satisfies Parameters<typeof useRepairOrdersBoard>[0];

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
    handleAppendParts,
    handleRemovePart,
    handleCloseOrder,
    renderRepairRow,
    statusFilter,
    handleStatusFilterChange,
    availableStatusFilters,
    getStatusLabel,
    search,
    handleSearchChange,
    dateFrom,
    dateTo,
    handleDateFromChange,
    handleDateToChange,
    showCreateForm: showCreateFormEnabled,
  } = useRepairOrdersBoard(hookOptions);

  // Resolver órdenes seleccionadas a partir del listado actual sin actualizar estado en efectos
  const selectedBudgetOrderResolved = useMemo(() => {
    return selectedBudgetOrder
      ? orders.find((order) => order.id === selectedBudgetOrder.id) ?? selectedBudgetOrder
      : null;
  }, [orders, selectedBudgetOrder]);

  const selectedPartsOrderResolved = useMemo(() => {
    return selectedPartsOrder
      ? orders.find((order) => order.id === selectedPartsOrder.id) ?? selectedPartsOrder
      : null;
  }, [orders, selectedPartsOrder]);

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
  searchPlaceholder={searchPlaceholder ?? "Buscar reparaciones"}
      totalOrders={orders.length}
      getStatusLabel={getStatusLabel}
      dateFrom={dateFrom}
      dateTo={dateTo}
      onDateFromChange={handleDateFromChange}
      onDateToChange={handleDateToChange}
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

  const toolbarPayload = { filters: filtersSection, actions: toolbarActions } as const;
  const toolbar = renderToolbar ? renderToolbar(toolbarPayload) : defaultToolbar;

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
        order={selectedBudgetOrderResolved}
        open={selectedBudgetOrderResolved !== null}
        onClose={() => setSelectedBudgetOrder(null)}
        onConfirmClose={
          selectedBudgetOrderResolved
            ? async () => {
                const success = await handleCloseOrder(selectedBudgetOrderResolved); // [PACK37-frontend]
                if (success) {
                  setSelectedBudgetOrder(null);
                }
              }
            : undefined
        }
      />

      <PartsModal
        order={selectedPartsOrderResolved}
        open={selectedPartsOrderResolved !== null}
        onClose={() => setSelectedPartsOrder(null)}
        resolveDeviceLabel={resolveDeviceLabel}
        devices={devices}
        onAppendParts={handleAppendParts}
        onRemovePart={handleRemovePart}
      />
    </section>
  );
}

export type { RepairOrdersBoardProps };
export default RepairOrdersBoard;
