import { Suspense, useMemo, useState } from "react";
import { Wrench } from "lucide-react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import ModuleHeader, { type ModuleStatus } from "../../../shared/components/ModuleHeader";
import Tabs, { type TabOption } from "../../../shared/components/ui/Tabs/Tabs";
import Loader from "../../../components/common/Loader";
import { useRepairsModule } from "../hooks/useRepairsModule";
import RepairsLayoutContext from "./context/RepairsLayoutContext";

type RepairTabId = "pendientes" | "finalizadas" | "repuestos" | "presupuestos";

type RepairTabConfig = {
  id: RepairTabId;
  label: string;
  path: string;
};

const REPAIR_TABS: RepairTabConfig[] = [
  { id: "pendientes", label: "Pendientes", path: "pendientes" },
  { id: "finalizadas", label: "Finalizadas", path: "finalizadas" },
  { id: "repuestos", label: "Repuestos", path: "repuestos" },
  { id: "presupuestos", label: "Presupuestos", path: "presupuestos" },
];

function resolveActiveTab(pathname: string): RepairTabId {
  const match = REPAIR_TABS.find((tab) => pathname.includes(tab.path));
  return match?.id ?? "pendientes";
}

function RepairsPage() {
  const {
    token,
    stores,
    selectedStoreId,
    setSelectedStoreId,
    refreshInventoryAfterTransfer,
    enablePurchasesSales,
  } = useRepairsModule();
  const [moduleStatus, setModuleStatus] = useState<ModuleStatus>(enablePurchasesSales ? "ok" : "warning");
  const [moduleStatusLabel, setModuleStatusLabel] = useState(
    enablePurchasesSales
      ? "Reparaciones al día"
      : "Activa SOFTMOBILE_ENABLE_PURCHASES_SALES para habilitar reparaciones",
  );

  const location = useLocation();
  const navigate = useNavigate();
  const activeTab = resolveActiveTab(location.pathname);

  const tabs = useMemo<TabOption<RepairTabId>[]>(
    () =>
      REPAIR_TABS.map((tab) => ({
        id: tab.id,
        label: tab.label,
        content: null,
      })),
    [],
  );

  const handleTabChange = (tabId: RepairTabId) => {
    const target = REPAIR_TABS.find((tab) => tab.id === tabId);
    if (!target) {
      return;
    }
    navigate(target.path);
  };

  const handleModuleStatusChange = (status: ModuleStatus, label: string) => {
    setModuleStatus(status);
    setModuleStatusLabel(label);
  };

  if (!enablePurchasesSales) {
    return (
      <div className="module-content">
        <ModuleHeader
          icon={<Wrench aria-hidden="true" />}
          title="Reparaciones"
          subtitle="Seguimiento de órdenes y control de piezas vinculadas al inventario"
          status="warning"
          statusLabel="Activa SOFTMOBILE_ENABLE_PURCHASES_SALES para habilitar reparaciones"
        />
        <section className="card">
          <h2>Órdenes de reparación</h2>
          <p className="muted-text">
            Activa <code>SOFTMOBILE_ENABLE_PURCHASES_SALES</code> para habilitar el flujo de reparaciones y sus ajustes de
            inventario vinculados.
          </p>
        </section>
      </div>
    );
  }

  const contextValue = {
    token,
    stores,
    selectedStoreId: selectedStoreId ?? null,
    setSelectedStoreId,
    onInventoryRefresh: refreshInventoryAfterTransfer,
    moduleStatus,
    moduleStatusLabel,
    setModuleStatus: handleModuleStatusChange,
  };

  return (
    <div className="module-content">
      <ModuleHeader
        icon={<Wrench aria-hidden="true" />}
        title="Reparaciones"
        subtitle="Seguimiento de órdenes y control de piezas vinculadas al inventario"
        status={moduleStatus}
        statusLabel={moduleStatusLabel}
      />

      <Tabs tabs={tabs} activeTab={activeTab} onTabChange={handleTabChange} />

      <RepairsLayoutContext.Provider value={contextValue}>
        <Suspense fallback={<Loader message="Cargando módulo de reparaciones…" />}>
          <Outlet />
        </Suspense>
      </RepairsLayoutContext.Provider>
    </div>
  );
}

export default RepairsPage;
