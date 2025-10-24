import { NavLink } from "react-router-dom";
import type { ReactNode } from "react";

type SidebarMenuItem = {
  to: string;
  label: string;
  icon?: ReactNode;
  description?: string;
};

type SidebarMenuProps = {
  items: SidebarMenuItem[];
  collapsed?: boolean;
  onNavigate?: () => void;
};

function SidebarMenu({ items, collapsed = false, onNavigate }: SidebarMenuProps) {
  return (
    <nav className="sidebar-menu">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          onClick={onNavigate}
          className={({ isActive }) =>
            ["sidebar-menu__item", isActive ? "is-active" : "", collapsed ? "is-collapsed" : ""].filter(Boolean).join(" ")
          }
          aria-label={collapsed ? item.label : undefined}
        >
          {item.icon ? (
            <span className="sidebar-menu__icon" aria-hidden="true">
              {item.icon}
            </span>
          ) : null}
          <span className="sidebar-menu__label">{item.label}</span>
          {item.description && !collapsed ? (
            <span className="sidebar-menu__description">{item.description}</span>
          ) : null}
        </NavLink>
      ))}
    </nav>
  );
}

export type { SidebarMenuItem, SidebarMenuProps };
export default SidebarMenu;
