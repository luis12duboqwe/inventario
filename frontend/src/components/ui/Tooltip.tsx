import type { ReactNode } from "react";
import styles from "./Tooltip.module.css";

type TooltipProps = {
  content: string;
  children: ReactNode;
  position?: "top" | "bottom" | "left" | "right";
};

function Tooltip({ content, children, position = "top" }: TooltipProps) {
  return (
    <div className={styles.tooltipWrapper} tabIndex={0} aria-label={content}>
      {children}
      <div className={`${styles.tooltip} ${styles[position]}`} role="tooltip">
        {content}
      </div>
    </div>
  );
}

export default Tooltip;
