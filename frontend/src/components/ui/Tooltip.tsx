import type { ReactNode } from "react";
import styles from "./Tooltip.module.css";

type TooltipProps = {
  content: string;
  children?: ReactNode;
  position?: "top" | "bottom" | "left" | "right";
};

function Tooltip({ content, children, position = "top" }: TooltipProps) {
  const trigger = children ?? (
    <span
      tabIndex={0}
      role="img"
      aria-label={`Ayuda: ${content}`}
      style={{ cursor: "help", fontSize: "0.85em" }}
    >
      ⓘ
    </span>
  );

  return (
    <div className={styles.tooltipWrapper}>
      {trigger}
      <div className={`${styles.tooltip} ${styles[position]}`} role="tooltip">
        {content}
      </div>
    </div>
  );
}

export default Tooltip;
