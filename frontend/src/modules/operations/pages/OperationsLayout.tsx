import React, { Suspense, useMemo } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Loader } from "../../../components/common/Loader";
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
    <section style={{ display: "grid", gap: 16 }}>
      <header style={{ display: "grid", gap: 12 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>Operaciones</h1>
        <PageToolbar searchPlaceholder="Buscar cliente, dispositivo o folio…" />
        <nav style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {tabs.map((t) => (
            <NavLink
              key={t.to}
              to={t.to}
              end
              style={({ isActive }) => ({
                padding: "8px 12px",
                borderRadius: 8,
                border: "1px solid rgba(255,255,255,0.08)",
                background: isActive ? "rgba(96,165,250,0.15)" : "rgba(255,255,255,0.03)",
                color: isActive ? "#cfe8ff" : "#cbd5e1",
                textDecoration: "none",
                fontSize: 13,
              })}
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

      <footer style={{ fontSize: 12, color: "#94a3b8" }}>
        Ruta actual: <code>{pathname}</code>
      </footer>
    </section>
  );
}
