import { Suspense, lazy, memo } from "react";
import { BellRing } from "lucide-react";

import ModuleHeader, { type ModuleStatus } from "../../../shared/components/ModuleHeader";
import { Skeleton } from "@components/ui/Skeleton";

const GlobalReportsDashboard = lazy(() => import("../components/GlobalReportsDashboard"));

const ReportsLoader = memo(function ReportsLoader() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Skeleton className="h-32 w-full rounded-xl" />
        <Skeleton className="h-32 w-full rounded-xl" />
        <Skeleton className="h-32 w-full rounded-xl" />
      </div>
      <Skeleton className="h-96 w-full rounded-xl" />
    </div>
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
