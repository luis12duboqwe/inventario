import React, { Suspense, useMemo } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Loader } from "../../../components/common/Loader";
import { PageToolbar } from "../../../components/layout/PageToolbar";

type OperationsTab = {
  to: string;
  label: string;
  description?: string;
  active: boolean;
};

export default function OperationsLayout() {
  const { pathname } = useLocation();

  const tabs = useMemo<OperationsTab[]>(() => {
    const basePath = "/dashboard/operations";
    const normalized = pathname.startsWith(basePath) ? pathname : `${basePath}`;
    const isInSales = normalized.startsWith(`${basePath}/ventas/`);
    const isInReturns = normalized.startsWith(`${basePath}/ventas/facturacion`);
    const isInPurchases = normalized.startsWith(`${basePath}/compras/`);
    const isInTransfers = normalized.startsWith(`${basePath}/movimientos/transferencias`);

    return [
      {
        to: "ventas",
        label: "POS y ventas",
        description: "Caja, clientes y sesiones",
        active: isInSales && !isInReturns,
      },
      {
        to: "compras",
        label: "Compras",
        description: "Órdenes, pagos y proveedores",
        active: isInPurchases,
      },
      {
        to: "ventas/facturacion",
        label: "Devoluciones",
        description: "Notas de crédito y ajustes",
        active: isInReturns,
      },
      {
        to: "movimientos/transferencias",
        label: "Transferencias",
        description: "Traslados entre sucursales",
        active: isInTransfers,
      },
    ];
  }, [pathname]);

  return (
    <section style={{ display: "grid", gap: 16 }}>
      <header style={{ display: "grid", gap: 12 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>Operaciones</h1>
        <PageToolbar searchPlaceholder="Buscar cliente, dispositivo o folio…" />
        <nav style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {tabs.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              style={() => ({
                padding: "10px 14px",
                borderRadius: 10,
                border: "1px solid rgba(148, 163, 184, 0.25)",
                background: tab.active ? "rgba(56, 189, 248, 0.18)" : "rgba(15, 23, 42, 0.35)",
                color: tab.active ? "#e0f2fe" : "#cbd5f5",
                textDecoration: "none",
                fontSize: 13,
                display: "grid",
                gap: 4,
                minWidth: 160,
              })}
              aria-current={tab.active ? "page" : undefined}
            >
              <span style={{ fontWeight: 600 }}>{tab.label}</span>
              {tab.description ? (
                <span style={{ fontSize: 12, color: tab.active ? "#bae6fd" : "#94a3b8" }}>{tab.description}</span>
              ) : null}
            </NavLink>
          ))}
        </nav>
      </header>

      <main>
        <Suspense fallback={<Loader variant="overlay" label="Cargando operaciones…" />}>
          <Outlet />
        </Suspense>
      </main>
    </section>
  );
}
