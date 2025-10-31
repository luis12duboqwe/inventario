import { Suspense, lazy, memo } from "react";
import { BellRing } from "lucide-react";

import ModuleHeader, { type ModuleStatus } from "../../../shared/components/ModuleHeader";

const GlobalReportsDashboard = lazy(() => import("../components/GlobalReportsDashboard"));

const ReportsLoader = memo(function ReportsLoader() {
  return (
    <section className="card" role="status" aria-live="polite">
      <div className="loading-overlay compact">
        <span className="spinner" aria-hidden="true" />
        <span>Cargando reportes corporativos…</span>
      </div>
    </section>
  );
});

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
      <Suspense fallback={<ReportsLoader />}>
        <GlobalReportsDashboard />
      </Suspense>
    </div>
  );
}

export default GlobalReportsPage;
