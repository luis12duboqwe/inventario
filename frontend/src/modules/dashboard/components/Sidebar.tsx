import { type ReactNode, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, PanelsTopLeft } from "lucide-react";

import SidebarMenu, { type SidebarMenuItem } from "../../../components/ui/SidebarMenu";

export type SidebarNavItem = {
  to: string;
  label: string;
  icon: ReactNode;
};

type SidebarProps = {
  items: SidebarNavItem[];
  currentPath: string;
  mobileOpen?: boolean;
  onNavigate?: () => void;
};

const STORAGE_KEY = "softmobile_sidebar_collapsed";

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

  const sidebarClassName = ["app-sidebar", collapsed ? "is-collapsed" : "", mobileOpen ? "is-mobile-open" : ""]
    .filter(Boolean)
    .join(" ");

  const menuItems: SidebarMenuItem[] = useMemo(
    () =>
      items.map((item) => ({
        to: item.to,
        label: item.label,
        icon: item.icon,
      })),
    [items],
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
