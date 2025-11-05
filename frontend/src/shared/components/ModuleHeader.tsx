import { type ReactNode } from "react";
import { motion } from "framer-motion";

import PageHeader, { type PageHeaderStatus } from "./ui/PageHeader";

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

const statusToneMap: Record<ModuleStatus, PageHeaderStatus["tone"]> = {
  ok: "ok",
  warning: "warning",
  critical: "critical",
};

function ModuleHeader({ icon, title, subtitle, status, statusLabel, actions }: Props) {
  const resolvedStatus: PageHeaderStatus | undefined = status
    ? {
        tone: statusToneMap[status],
        label: statusLabel ?? statusLabels[status],
      }
    : undefined;

  return (
    <motion.div
      className="module-header"
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
    >
      <PageHeader
        className="module-header__inner"
        leadingIcon={icon}
        title={title}
        description={subtitle}
        {...(resolvedStatus ? { status: resolvedStatus } : {})}
        {...(actions ? { actions } : {})}
      />
    </motion.div>
  );
}

export default ModuleHeader;
