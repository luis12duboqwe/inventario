import { type ReactNode, useId } from "react";

import styles from "./Tabs.module.css";

export type TabOption<TValue extends string = string> = {
  id: TValue;
  label: string;
  icon?: ReactNode;
  content: ReactNode;
};

type TabsProps<TValue extends string = string> = {
  tabs: TabOption<TValue>[];
  activeTab: TValue;
  onTabChange: (tabId: TValue) => void;
};

function Tabs<TValue extends string>({ tabs, activeTab, onTabChange }: TabsProps<TValue>) {
  const tabListId = useId();

  return (
    <div className={styles.tabs}>
      <div className={styles.tabList} role="tablist" aria-label="Subsecciones del módulo" id={tabListId}>
        {tabs.map((tab) => {
          const isActive = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              type="button"
              className={`${styles.tabTrigger} ${isActive ? styles.active : ""}`}
              role="tab"
              aria-selected={isActive}
              aria-controls={`${tabListId}-${tab.id}`}
              id={`${tabListId}-trigger-${tab.id}`}
              onClick={() => onTabChange(tab.id)}
            >
              {tab.icon ? <span className={styles.icon}>{tab.icon}</span> : null}
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>
      {tabs.map((tab) => {
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
