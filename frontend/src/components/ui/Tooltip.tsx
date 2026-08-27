import type { ReactNode } from "react";
import styles from "./Tooltip.module.css";

type TooltipProps = {
  content: string;
  children?: ReactNode;
  position?: "top" | "bottom" | "left" | "right";
};

const DEFAULT_TOOLTIP_POSITION: NonNullable<TooltipProps["position"]> = "top";

function Tooltip({ content, children, position = DEFAULT_TOOLTIP_POSITION }: TooltipProps) {
  const trigger = children ?? (
    <button
      type="button"
      aria-label={`Ayuda: ${content}`}
      style={{
        border: 0,
        padding: 0,
        background: "transparent",
        color: "inherit",
        cursor: "help",
        font: "inherit",
      }}
    >
      ⓘ
    </button>
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

export { Tooltip };
export type { TooltipProps };
export default Tooltip;
