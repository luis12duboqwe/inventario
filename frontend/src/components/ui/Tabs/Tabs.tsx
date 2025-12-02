import { type ReactNode, useId } from "react";
import { Link } from "react-router-dom";

import styles from "./Tabs.module.css";

export type TabOption<TValue extends string = string> = {
  id: TValue;
  label: string;
  icon?: ReactNode;
  content?: ReactNode;
  href?: string;
};

type TabsProps<TValue extends string = string> = {
  tabs: TabOption<TValue>[];
  activeTab: TValue;
  onTabChange: (tabId: TValue) => void;
  mode?: "tabs" | "navigation";
};

function Tabs<TValue extends string>({
  tabs,
  activeTab,
  onTabChange,
  mode = "tabs",
}: TabsProps<TValue>) {
  const tabListId = useId();
  const isNavigation = mode === "navigation";

  return (
    <div className={styles.tabs}>
      <div
        className={styles.tabList}
        role={isNavigation ? "navigation" : "tablist"}
        aria-label="Subsecciones del módulo"
        id={tabListId}
      >
        {tabs.map((tab) => {
          const isActive = tab.id === activeTab;
          const className = `${styles.tabTrigger} ${isActive ? styles.active : ""}`;

          if (isNavigation && tab.href) {
            return (
              <Link
                key={tab.id}
                to={tab.href}
                className={className}
                aria-current={isActive ? "page" : undefined}
                id={`${tabListId}-trigger-${tab.id}`}
                onClick={() => onTabChange(tab.id)}
              >
                {tab.icon ? <span className={styles.icon}>{tab.icon}</span> : null}
                <span>{tab.label}</span>
              </Link>
            );
          }

          return (
            <button
              key={tab.id}
              type="button"
              className={className}
              role={isNavigation ? undefined : "tab"}
              aria-selected={isNavigation ? undefined : isActive}
              aria-current={isNavigation && isActive ? "page" : undefined}
              aria-controls={isNavigation ? undefined : `${tabListId}-${tab.id}`}
              id={`${tabListId}-trigger-${tab.id}`}
              onClick={() => onTabChange(tab.id)}
            >
              {tab.icon ? <span className={styles.icon}>{tab.icon}</span> : null}
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>
      {mode === "tabs" &&
        tabs.map((tab) => {
          const isActive = tab.id === activeTab;
          return (
            <section
              key={tab.id}
              role="tabpanel"
              id={`${tabListId}-${tab.id}`}
              aria-labelledby={`${tabListId}-trigger-${tab.id}`}
              hidden={!isActive}
              className={styles.tabPanel}
            >
              {isActive ? tab.content : null}
            </section>
          );
        })}
    </div>
  );
}

export default Tabs;
