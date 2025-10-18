import { BellRing } from "lucide-react";

import ModuleHeader, { type ModuleStatus } from "../../../components/ModuleHeader";
import GlobalReportsDashboard from "../components/GlobalReportsDashboard";

function GlobalReportsPage() {
  const status: ModuleStatus = "ok";

  return (
    <div className="module-content">
      <ModuleHeader
        icon={<BellRing aria-hidden="true" />}
        title="Reportes globales"
        subtitle="Alertas corporativas, bitácoras consolidadas y exportaciones ejecutivas en tema oscuro."
        status={status}
        statusLabel="Monitoreo activo"
      />
      <GlobalReportsDashboard />
    </div>
  );
}

export default GlobalReportsPage;
