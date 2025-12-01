import React, { Suspense, useMemo } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Loader } from "@components/ui/Loader";
import { PageToolbar } from "../../../components/layout/PageToolbar";
import { useDashboard } from "../../dashboard/context/DashboardContext";

export default function OperationsLayout() {
  const { pathname } = useLocation();
  const { enableBundles, enableDte } = useDashboard();
  const tabs = useMemo(() => {
    const base = [
      { to: "pos", label: "POS / Caja" },
      { to: "compras", label: "Compras" },
      { to: "devoluciones", label: "Devoluciones" },
      { to: "garantias", label: "Garantías" },
      { to: "transferencias", label: "Transferencias" },
      { to: "diagnosticos", label: "Diagnósticos" },
    ];

    if (enableBundles) {
      base.push({ to: "paquetes", label: "Paquetes" });
    }

    if (enableDte) {
      base.push({ to: "dte", label: "DTE" });
    }

    return base;
  }, [enableBundles, enableDte]);
  return (
    <section className="operations-layout">
      <header className="operations-layout__header">
        <h1 className="operations-layout__title">Operaciones</h1>
        <PageToolbar searchPlaceholder="Buscar cliente, dispositivo o folio…" />
        <nav className="operations-layout__nav">
          {tabs.map((t) => (
            <NavLink
              key={t.to}
              to={t.to}
              end
              className={({ isActive }) =>
                `operations-layout__nav-link ${
                  isActive ? "operations-layout__nav-link--active" : ""
                }`
              }
            >
              {t.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main>
        <Suspense fallback={<Loader variant="overlay" label="Cargando operaciones…" />}>
          <Outlet />
        </Suspense>
      </main>

      <footer className="operations-layout__footer">
        Ruta actual: <code>{pathname}</code>
      </footer>
    </section>
  );
}
