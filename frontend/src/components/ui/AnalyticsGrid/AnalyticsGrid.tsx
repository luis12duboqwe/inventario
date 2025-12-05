import type { ReactNode } from "react";

import styles from "./AnalyticsGrid.module.css";

export type AnalyticsGridItem = {
  id: string;
  title: ReactNode;
  description?: string;
  content: ReactNode;
};

type AnalyticsGridProps = {
  items: AnalyticsGridItem[];
};

function AnalyticsGrid({ items }: AnalyticsGridProps) {
  return (
    <div className={styles.grid}>
      {items.map((item) => (
        <section key={item.id} className={`analytics-panel ${styles.card}`}>
          <header className={styles.header}>
            <h3 className="accent-title">{item.title}</h3>
            {item.description ? <p className="card-subtitle">{item.description}</p> : null}
          </header>
          <div className={styles.content}>{item.content}</div>
        </section>
      ))}
    </div>
  );
}

export default AnalyticsGrid;
