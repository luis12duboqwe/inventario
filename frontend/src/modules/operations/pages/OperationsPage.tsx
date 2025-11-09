import { Suspense, memo, useMemo } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { Cog } from "lucide-react";

import Loader from "../../../components/common/Loader";
import ModuleHeader, { type ModuleStatus } from "../../../shared/components/ModuleHeader";
import { useOperationsModule } from "../hooks/useOperationsModule";

const OperationsContentFallback = memo(function OperationsContentFallback() {
  return <Loader message="Cargando vista de operaciones…" />;
});

type SubRouteLink = {
  id: string;
  to: string;
  label: string;
  description: string;
  disabled?: boolean;
};

const baseOperationsNavigation: Array<{
  id: string;
  title: string;
  links: SubRouteLink[];
}> = [
  {
    id: "ventas",
    title: "Ventas",
    links: [
      { id: "ventas-caja", to: "ventas/caja", label: "Caja", description: "Cobros rápidos y conciliaciones" },
      { id: "ventas-facturacion", to: "ventas/facturacion", label: "Facturación", description: "Ventas, notas y devoluciones" },
      { id: "ventas-clientes", to: "ventas/clientes", label: "Clientes", description: "Cartera, notas y métricas" },
      { id: "ventas-cajas", to: "ventas/cajas", label: "Cajas", description: "Historial de sesiones" },
    ],
  },
  {
    id: "compras",
    title: "Compras",
    links: [
      { id: "compras-ordenes", to: "compras/ordenes", label: "Órdenes", description: "Recepciones y costos" },
      { id: "compras-pagos", to: "compras/pagos", label: "Pagos", description: "Desembolsos y notas" },
      { id: "compras-proveedores", to: "compras/proveedores", label: "Proveedores", description: "Catálogo y lotes" },
    ],
  },
  {
    id: "movimientos",
    title: "Logística",
    links: [
      {
        id: "movimientos-internos",
        to: "movimientos/internos",
        label: "Movimientos internos",
        description: "Ajustes y conteos",
      },
      {
        id: "movimientos-transferencias",
        to: "movimientos/transferencias",
        label: "Transferencias",
        description: "Entre sucursales",
      },
    ],
  },
  {
    id: "garantias",
    title: "Garantías",
    links: [
      {
        id: "garantias-panel",
        to: "garantias",
        label: "Gestión",
        description: "Cobertura y reclamos",
      },
    ],
  },
];

function OperationsPage() {
  const { enablePurchasesSales, enableTransfers } = useOperationsModule();

  const navigation = useMemo(() => {
    return baseOperationsNavigation.map((group) => ({
      ...group,
      links: group.links.map((link) => ({
        ...link,
        disabled:
          !enablePurchasesSales && (group.id === "ventas" || group.id === "compras")
            ? true
            : link.id === "movimientos-transferencias" && !enableTransfers
              ? true
              : group.id === "garantias" && !enablePurchasesSales
                ? true
                : link.disabled,
      })),
    }));
  }, [enablePurchasesSales, enableTransfers]);

  const moduleStatus = useMemo<ModuleStatus>(() => {
    if (!enablePurchasesSales && !enableTransfers) {
      return "critical";
    }
    if (!enablePurchasesSales || !enableTransfers) {
      return "warning";
    }
    return "ok";
  }, [enablePurchasesSales, enableTransfers]);

  const moduleStatusLabel = useMemo(() => {
    if (!enablePurchasesSales && !enableTransfers) {
      return "Operaciones deshabilitadas. Activa los flags corporativos";
    }
    if (!enablePurchasesSales || !enableTransfers) {
      return "Revisa las funciones pendientes por activar";
    }
    return "Flujos de operaciones activos";
  }, [enablePurchasesSales, enableTransfers]);

  return (
    <div className="module-content operations-module">
      <ModuleHeader
        icon={<Cog aria-hidden="true" />}
        title="Operaciones"
        subtitle="Compras, ventas, devoluciones y transferencias sincronizadas con inventario"
        status={moduleStatus}
        statusLabel={moduleStatusLabel}
      />

      <nav className="operations-subnav" aria-label="Subrutas de operaciones">
        {navigation.map((group) => (
          <div key={group.id} className="operations-subnav__group">
            <p className="operations-subnav__title">{group.title}</p>
            <ul className="operations-subnav__list">
              {group.links.map((link) => (
                <li key={link.id} className="operations-subnav__item">
                  <NavLink
                    to={link.to}
                    className={({ isActive }) =>
                      [
                        "operations-subnav__link",
                        isActive ? "operations-subnav__link--active" : null,
                        link.disabled ? "operations-subnav__link--disabled" : null,
                      ]
                        .filter(Boolean)
                        .join(" ")
                    }
                    aria-disabled={link.disabled}
                    tabIndex={link.disabled ? -1 : 0}
                  >
                    <span className="operations-subnav__link-label">{link.label}</span>
                    <span className="operations-subnav__link-desc">{link.description}</span>
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <Suspense fallback={<OperationsContentFallback />}>
        <div className="operations-subpage-container">
          <Outlet />
        </div>
      </Suspense>
    </div>
  );
}

export default OperationsPage;
