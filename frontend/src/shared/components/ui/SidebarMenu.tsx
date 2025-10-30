import { NavLink } from "react-router-dom";
import type { ReactNode } from "react";

type SidebarMenuChild = {
  to: string;
  label: string;
};

type SidebarMenuItem = {
  to: string;
  label: string;
  icon?: ReactNode;
  description?: string;
  children?: SidebarMenuChild[];
  onMouseEnter?: () => void;
};

type SidebarMenuProps = {
  items: SidebarMenuItem[];
  collapsed?: boolean;
  onNavigate?: () => void;
};

function SidebarMenu({ items, collapsed = false, onNavigate }: SidebarMenuProps) {
  return (
    <nav className="sidebar-menu">
      {items.map((item) => {
        const hasChildren = (item.children?.length ?? 0) > 0;

        if (!hasChildren) {
          return (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onNavigate}
              className={({ isActive }) =>
                ["sidebar-menu__item", isActive ? "is-active" : "", collapsed ? "is-collapsed" : ""]
                  .filter(Boolean)
                  .join(" ")
              }
              aria-label={collapsed ? item.label : undefined}
              onMouseEnter={item.onMouseEnter}
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
          );
        }

        return (
          <div key={item.to} className={["sidebar-menu__group", collapsed ? "is-collapsed" : ""].filter(Boolean).join(" ")}>
            <NavLink
              to={item.to}
              onClick={onNavigate}
              className={({ isActive }) =>
                [
                  "sidebar-menu__item",
                  hasChildren ? "has-children" : "",
                  isActive ? "is-active" : "",
                  collapsed ? "is-collapsed" : "",
                ]
                  .filter(Boolean)
                  .join(" ")
              }
              aria-label={collapsed ? item.label : undefined}
              aria-expanded={!collapsed}
              onMouseEnter={item.onMouseEnter}
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
            {!collapsed ? (
              <div className="sidebar-menu__children">
                {item.children?.map((child) => (
                  <NavLink
                    key={child.to}
                    to={child.to}
                    onClick={onNavigate}
                    className={({ isActive }) =>
                      ["sidebar-menu__child", isActive ? "is-active" : ""].filter(Boolean).join(" ")
                    }
                  >
                    <span className="sidebar-menu__child-label">{child.label}</span>
                  </NavLink>
                ))}
              </div>
            ) : null}
          </div>
        );
      })}
    </nav>
  );
}

export type { SidebarMenuChild, SidebarMenuItem, SidebarMenuProps };
export default SidebarMenu;
