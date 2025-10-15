import { type ReactNode, useMemo, useState } from "react";
import { NavLink } from "react-router-dom";
import { ChevronLeft, ChevronRight, PanelsTopLeft } from "lucide-react";

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

  const sidebarClassName = [
    "dashboard-sidebar",
    collapsed ? "collapsed" : "",
    mobileOpen ? "mobile-open" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <aside id="dashboard-navigation" className={sidebarClassName} aria-label="Menú principal">
      <div className="dashboard-sidebar__brand">
        <span className="dashboard-sidebar__brand-icon" aria-hidden="true">
          <PanelsTopLeft size={20} />
        </span>
        <div className="dashboard-sidebar__brand-text">
          <strong>Softmobile 2025</strong>
          <span>v2.2.0 · {activeLabel}</span>
        </div>
      </div>
      <nav className="dashboard-sidebar__nav">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `dashboard-sidebar__link${isActive ? " active" : ""}`
            }
            aria-label={collapsed ? item.label : undefined}
            onClick={handleNavigate}
          >
            <span className="dashboard-sidebar__icon" aria-hidden="true">
              {item.icon}
            </span>
            <span className="dashboard-sidebar__label">{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <button
        type="button"
        className="dashboard-sidebar__toggle"
        onClick={handleToggle}
        aria-pressed={collapsed}
        aria-label={toggleLabel}
        title={toggleLabel}
      >
        <span aria-hidden="true">{collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}</span>
        <span className="dashboard-sidebar__toggle-label">{toggleLabel}</span>
      </button>
    </aside>
  );
}

export default Sidebar;
