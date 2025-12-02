import { useState } from "react";
import type { ReactNode } from "react";

import styles from "./Accordion.module.css";

export type AccordionItem<TValue extends string = string> = {
  id: TValue;
  title: string;
  description?: string;
  content: ReactNode;
  defaultOpen?: boolean;
};

type AccordionProps<TValue extends string = string> = {
  items: AccordionItem<TValue>[];
  allowMultiple?: boolean;
};

function Accordion<TValue extends string>({ items, allowMultiple = true }: AccordionProps<TValue>) {
  const [openItems, setOpenItems] = useState<Set<TValue>>(() => {
    const defaults = items.filter((item) => item.defaultOpen).map((item) => item.id);
    return new Set(defaults);
  });

  const toggleItem = (itemId: TValue) => {
    setOpenItems((current) => {
      const next = new Set(current);
      const isActive = next.has(itemId);
      if (allowMultiple) {
        if (isActive) {
          next.delete(itemId);
        } else {
          next.add(itemId);
        }
        return next;
      }
      if (isActive) {
        next.delete(itemId);
        return next;
      }
      return new Set([itemId]);
    });
  };

  return (
    <div className={styles.accordion}>
      {items.map((item) => {
        const isOpen = openItems.has(item.id);
        return (
          <article key={item.id} className={`${styles.item} ${isOpen ? styles.expanded : ""}`}>
            <header className={styles.header}>
              <button
                type="button"
                className={styles.trigger}
                aria-expanded={isOpen}
                aria-controls={`${item.id}-content`}
                id={`${item.id}-trigger`}
                onClick={() => toggleItem(item.id)}
              >
                <div className={styles.headerText}>
                  <span className={styles.title}>{item.title}</span>
                  {item.description ? <span className={styles.description}>{item.description}</span> : null}
                </div>
                <span className={styles.icon} aria-hidden>
                  {isOpen ? "−" : "+"}
                </span>
              </button>
            </header>
            <div
              id={`${item.id}-content`}
              role="region"
              aria-labelledby={`${item.id}-trigger`}
              className={styles.content}
              hidden={!isOpen}
            >
              {isOpen ? item.content : null}
            </div>
          </article>
        );
      })}
    </div>
  );
}

export default Accordion;
