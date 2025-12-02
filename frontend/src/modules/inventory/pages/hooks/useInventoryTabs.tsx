import { useLocation, useNavigate } from "react-router-dom";
import { useMemo, type ReactNode } from "react";
import {
  AlertTriangle,
  Boxes,
  Building2,
  DollarSign,
  RefreshCcw,
  ShieldCheck,
} from "lucide-react";

export type InventoryTabId =
  | "productos"
  | "listas"
  | "movimientos"
  | "proveedores"
  | "alertas"
  | "reservas";

export interface InventoryTab {
  id: InventoryTabId;
  label: string;
  icon: ReactNode;
  path: string;
}

export function useInventoryTabs(enablePriceLists: boolean) {
  const location = useLocation();
  const navigate = useNavigate();

  const tabs = useMemo<InventoryTab[]>(() => [
    {
      id: "productos",
      label: "Productos",
      icon: <Boxes size={16} aria-hidden="true" />,
      path: "productos",
    },
    {
      id: "listas",
      label: "Listas de precios",
      icon: <DollarSign size={16} aria-hidden="true" />,
      path: "listas",
    },
    {
      id: "movimientos",
      label: "Movimientos",
      icon: <RefreshCcw size={16} aria-hidden="true" />,
      path: "movimientos",
    },
    {
      id: "proveedores",
      label: "Proveedores",
      icon: <Building2 size={16} aria-hidden="true" />,
      path: "proveedores",
    },
    {
      id: "alertas",
      label: "Alertas",
      icon: <AlertTriangle size={16} aria-hidden="true" />,
      path: "alertas",
    },
    {
      id: "reservas",
      label: "Reservas",
      icon: <ShieldCheck size={16} aria-hidden="true" />,
      path: "reservas",
    },
  ], []);

  const activeTab = useMemo<InventoryTabId>(() => {
    const pathname = location.pathname;
    if (pathname.includes("/movimientos")) return "movimientos";
    if (pathname.includes("/listas-precios")) return "listas";
    if (pathname.includes("/proveedores")) return "proveedores";
    if (pathname.includes("/alertas")) return "alertas";
    if (pathname.includes("/reservas")) return "reservas";
    if (pathname.includes("/listas") && enablePriceLists) return "listas";
    return "productos";
  }, [location.pathname, enablePriceLists]);

  const handleTabChange = (tabId: InventoryTabId) => {
    const tab = tabs.find((t) => t.id === tabId);
    if (tab) {
      navigate(tab.path);
    }
  };

  return { tabs, activeTab, handleTabChange };
}
