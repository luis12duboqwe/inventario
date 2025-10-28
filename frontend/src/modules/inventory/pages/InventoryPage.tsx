import { Suspense, lazy, useMemo } from "react";
import { Boxes } from "lucide-react";
import { Outlet } from "react-router-dom";

import ModuleHeader from "../../../shared/components/ModuleHeader";
import LoadingOverlay from "../../../shared/components/LoadingOverlay";
import Tabs, { type TabOption } from "../../../shared/components/ui/Tabs/Tabs";
import Loader from "../../../components/common/Loader";
import InventoryLayoutContext from "./context/InventoryLayoutContext";
import { useInventoryLayoutState, type InventoryTabId } from "./useInventoryLayoutState";

const DeviceEditDialog = lazy(() => import("../components/DeviceEditDialog"));

function InventoryPage() {
  const {
    contextValue,
    tabOptions,
    activeTab,
    handleTabChange,
    moduleStatus,
    moduleStatusLabel,
    loading,
    editingDevice,
    isEditDialogOpen,
    closeEditDialog,
    handleSubmitDeviceUpdates,
  } = useInventoryLayoutState();

  const tabs = useMemo<TabOption<InventoryTabId>[]>(
    () =>
      tabOptions.map((tab) => ({
        id: tab.id,
        label: tab.label,
        icon: tab.icon,
      })),
    [tabOptions],
  );

  return (
    <div className="module-content inventory-module">
      <ModuleHeader
        icon={<Boxes aria-hidden="true" />}
        title="Inventario corporativo"
        subtitle="Gestión de existencias, auditoría de movimientos y respaldos en tiempo real"
        status={moduleStatus}
        statusLabel={moduleStatusLabel}
      />

      <LoadingOverlay visible={loading} label="Sincronizando inventario..." />

      <Tabs tabs={tabs} activeTab={activeTab} onTabChange={handleTabChange} />

      <InventoryLayoutContext.Provider value={contextValue}>
        <Suspense fallback={<Loader message="Cargando vista de inventario…" />}>
          <Outlet />
        </Suspense>
        <Suspense fallback={null}>
          <DeviceEditDialog
            device={editingDevice}
            open={isEditDialogOpen}
            onClose={closeEditDialog}
            onSubmit={handleSubmitDeviceUpdates}
          />
        </Suspense>
      </InventoryLayoutContext.Provider>
    </div>
  );
}

export default InventoryPage;
