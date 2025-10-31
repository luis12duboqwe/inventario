import { type ReactNode, useCallback, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, PanelsTopLeft } from "lucide-react";

import SidebarMenu, { type SidebarMenuItem } from "../../../shared/components/ui/SidebarMenu";
// [PACK25-PREFETCH-WIRE-START]
import { preimport, prefetchJson } from "@/lib/prefetch";
// [PACK25-PREFETCH-WIRE-END]

export type SidebarNavChild = {
  to: string;
  label: string;
};

export type SidebarNavItem = {
  to: string;
  label: string;
  icon: ReactNode;
  children?: SidebarNavChild[];
  onMouseEnter?: () => void;
};

type SidebarProps = {
  items: SidebarNavItem[];
  currentPath: string;
  mobileOpen?: boolean;
  onNavigate?: () => void;
};

const STORAGE_KEY = "softmobile_sidebar_collapsed";
const BASE = (import.meta as any)?.env?.VITE_API_BASE_URL || "";

function Sidebar({ items, currentPath, mobileOpen = false, onNavigate }: SidebarProps) {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    if (typeof window === "undefined") {
      return false;
    }
    return window.localStorage.getItem(STORAGE_KEY) === "1";
  });

  const toggleLabel = collapsed ? "Expandir menú" : "Colapsar menú";

  const activeLabel = useMemo(() => {
    const activeItem = items.find((item) => currentPath.startsWith(item.to));
    return activeItem?.label ?? "Softmobile";
  }, [currentPath, items]);

  const handleToggle = () => {
    setCollapsed((current) => {
      const next = !current;
      if (typeof window !== "undefined") {
        window.localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
      }
      return next;
    });
  };

  const handleNavigate = () => {
    onNavigate?.();
  };

  const onHoverSales = useCallback(() => {
    preimport(() => import("@/modules/sales/pages/POSPage"));
    preimport(() => import("@/modules/sales/pages/QuotesListPage"));
    preimport(() => import("@/modules/sales/pages/CustomersListPage"));

    prefetchJson(`${BASE}/api/products/search?page=1&pageSize=12`);
    prefetchJson(`${BASE}/api/customers?page=1&pageSize=20`);
  }, []);

  const sidebarClassName = ["app-sidebar", collapsed ? "is-collapsed" : "", mobileOpen ? "is-mobile-open" : ""]
    .filter(Boolean)
    .join(" ");

  const menuItems: SidebarMenuItem[] = useMemo(
    () =>
      items.map((item) => ({
        to: item.to,
        label: item.label,
        icon: item.icon,
        onMouseEnter: item.onMouseEnter ?? (item.label === "Ventas" ? onHoverSales : undefined),
        children: item.children?.map((child) => ({
          to: child.to,
          label: child.label,
        })),
      })),
    [items, onHoverSales],
  );

  return (
    <aside id="dashboard-navigation" className={sidebarClassName} aria-label="Menú principal">
      <div className="app-sidebar__brand">
        <span className="app-sidebar__brand-icon" aria-hidden="true">
          <PanelsTopLeft size={20} />
        </span>
        <div className="app-sidebar__brand-text">
          <strong>Softmobile 2025</strong>
          <span>v2.2.0 · {activeLabel}</span>
        </div>
      </div>
      <SidebarMenu items={menuItems} collapsed={collapsed} onNavigate={handleNavigate} />
      <button
        type="button"
        className="app-sidebar__toggle"
        onClick={handleToggle}
        aria-pressed={collapsed}
        aria-label={toggleLabel}
        title={toggleLabel}
      >
        <span aria-hidden="true">{collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}</span>
        <span className="app-sidebar__toggle-label">{toggleLabel}</span>
      </button>
    </aside>
  );
}

export default Sidebar;
