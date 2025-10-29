import React, { Suspense } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Loader } from "../../../components/common/Loader";
import { PageToolbar } from "../../../components/layout/PageToolbar";

export default function RepairsLayout() {
  const { pathname } = useLocation();
  const tabs = [
    { to: "pendientes", label: "Pendientes" },
    { to: "finalizadas", label: "Finalizadas" },
    { to: "repuestos", label: "Repuestos" },
    { to: "presupuestos", label: "Presupuestos" },
  ];

  return (
    <section style={{ display: "grid", gap: 16 }}>
      <header style={{ display: "grid", gap: 12 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>Reparaciones</h1>
        <PageToolbar searchPlaceholder="Buscar por cliente, técnico, daño o folio…" />
        <nav style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {tabs.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
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
              {tab.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main>
        <Suspense fallback={<Loader variant="overlay" label="Cargando reparaciones…" />}>
          <Outlet />
        </Suspense>
      </main>

      <footer style={{ fontSize: 12, color: "#94a3b8" }}>
        Ruta actual: <code>{pathname}</code>
      </footer>
    </section>
  );
}
