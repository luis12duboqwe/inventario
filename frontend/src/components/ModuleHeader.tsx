import { type ReactNode } from "react";
import { motion } from "framer-motion";

export type ModuleStatus = "ok" | "warning" | "critical";

type Props = {
  icon: ReactNode;
  title: string;
  subtitle: string;
  status?: ModuleStatus;
  statusLabel?: string;
  actions?: ReactNode;
};

const statusLabels: Record<ModuleStatus, string> = {
  ok: "Operativo",
  warning: "Atención",
  critical: "Crítico",
};

function ModuleHeader({ icon, title, subtitle, status, statusLabel, actions }: Props) {
  const resolvedLabel = status ? statusLabel ?? statusLabels[status] : undefined;

  return (
    <motion.header
      className="module-header"
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
    >
      <div className="module-header__icon" aria-hidden="true">
        {icon}
      </div>
      <div className="module-header__content">
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      {status ? (
        <div className={`status-indicator status-${status}`} role="status" aria-label={resolvedLabel}>
          <span className="status-indicator__dot" aria-hidden="true" />
          <span className="status-indicator__label">{resolvedLabel}</span>
        </div>
      ) : null}
      {actions ? <div className="module-header__actions">{actions}</div> : null}
    </motion.header>
  );
}

export default ModuleHeader;
