import { Suspense, useMemo, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import PageHeader from "../../components/layout/PageHeader";
import PageToolbar from "../../components/layout/PageToolbar";
import Loader from "../../components/common/Loader";
import { useRepairsModule } from "../../modules/repairs/hooks/useRepairsModule";
import RepairsLayoutContext, {
  type RepairsLayoutContextValue,
} from "../../modules/repairs/pages/context/RepairsLayoutContext";
import type { ModuleStatus } from "../../shared/components/ModuleHeader";

const REPARACIONES_TABS = [
  { id: "pendientes", label: "Pendientes", path: "pendientes" },
  { id: "en-proceso", label: "En proceso", path: "en-proceso" },
  { id: "listas", label: "Listas", path: "listas" },
  { id: "entregadas", label: "Entregadas", path: "entregadas" },
  { id: "repuestos", label: "Repuestos", path: "repuestos" },
  { id: "presupuestos", label: "Presupuestos", path: "presupuestos" },
] as const; // [PACK37-frontend]

type ReparacionesTabId = (typeof REPARACIONES_TABS)[number]["id"];

type ReparacionesTab = {
  id: ReparacionesTabId;
  label: string;
  path: string;
};

function ReparacionesLayout() {
  const {
    token,
    stores,
    selectedStoreId,
    setSelectedStoreId,
    refreshInventoryAfterTransfer,
    enablePurchasesSales,
  } = useRepairsModule();

  const [moduleStatus, setModuleStatus] = useState<ModuleStatus>(
    enablePurchasesSales ? "ok" : "warning",
  );
  const [moduleStatusLabel, setModuleStatusLabel] = useState(
    enablePurchasesSales
      ? "Reparaciones al día"
      : "Activa SOFTMOBILE_ENABLE_PURCHASES_SALES para habilitar reparaciones",
  );

  const tabs = useMemo<ReparacionesTab[]>(() => [...REPARACIONES_TABS], []);

  const handleModuleStatusChange = (status: ModuleStatus, label: string) => {
    setModuleStatus(status);
    setModuleStatusLabel(label);
  };

  // Nota: evitamos returns tempranos antes de invocar hooks; la UI se decide en render.

  const contextValue = useMemo<RepairsLayoutContextValue>(
    () => ({
      token,
      stores,
      selectedStoreId: selectedStoreId ?? null,
      setSelectedStoreId,
      onInventoryRefresh: refreshInventoryAfterTransfer,
      moduleStatus,
      moduleStatusLabel,
      setModuleStatus: handleModuleStatusChange,
    }),
    [
      moduleStatus,
      moduleStatusLabel,
      refreshInventoryAfterTransfer,
      selectedStoreId,
      setSelectedStoreId,
      stores,
      token,
    ],
  );

  return (
    <div className="reparaciones-layout">
      <PageHeader title="Reparaciones" subtitle="Órdenes y repuestos" />

      {!enablePurchasesSales ? (
        <section className="card">
          <h2>Órdenes de reparación</h2>
          <p className="muted-text">
            Activa <code>SOFTMOBILE_ENABLE_PURCHASES_SALES</code> para habilitar el flujo de
            reparaciones y sus ajustes de inventario vinculados.
          </p>
        </section>
      ) : (
        <>
          <PageToolbar>
            <div
              className={`reparaciones-status reparaciones-status--${moduleStatus}`}
              role="status"
              aria-live="polite"
            >
              <span className="reparaciones-status__dot" aria-hidden="true" />
              <span>{moduleStatusLabel}</span>
            </div>
          </PageToolbar>

          <nav className="reparaciones-tabs" aria-label="Secciones de reparaciones">
            {tabs.map((tab) => (
              <NavLink
                key={tab.id}
                to={tab.path}
                className={({ isActive }) =>
                  `reparaciones-tab${isActive ? " reparaciones-tab--active" : ""}`
                }
                end={tab.path === "pendientes"}
              >
                {tab.label}
              </NavLink>
            ))}
          </nav>

          <RepairsLayoutContext.Provider value={contextValue}>
            <Suspense
              fallback={
                <Loader label="Cargando módulo de reparaciones…" message="Cargando módulo de reparaciones…" />
              }
            >
              <Outlet />
            </Suspense>
          </RepairsLayoutContext.Provider>
        </>
      )}
    </div>
  );
}

export default ReparacionesLayout;
