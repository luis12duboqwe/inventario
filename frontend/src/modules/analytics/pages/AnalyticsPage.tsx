import { BarChart3 } from "lucide-react";

import AnalyticsBoard from "../components/AnalyticsBoard";
import ModuleHeader, { type ModuleStatus } from "../../../components/ModuleHeader";
import { useAnalyticsModule } from "../hooks/useAnalyticsModule";

function AnalyticsPage() {
  const { token, enableAnalyticsAdv } = useAnalyticsModule();

  const status: ModuleStatus = enableAnalyticsAdv ? "ok" : "warning";
  const statusLabel = enableAnalyticsAdv
    ? "Analítica avanzada activa"
    : "Activa SOFTMOBILE_ENABLE_ANALYTICS_ADV para habilitar reportes";

  return (
    <div className="module-content">
      <ModuleHeader
        icon={<BarChart3 aria-hidden="true" />}
        title="Analítica"
        subtitle="Proyecciones, márgenes y comparativos multi-sucursal en tiempo real"
        status={status}
        statusLabel={statusLabel}
      />
      {enableAnalyticsAdv ? (
        <AnalyticsBoard token={token} />
      ) : (
        <section className="card">
          <h2>Analítica avanzada</h2>
          <p className="muted-text">
            Activa el flag corporativo <code>SOFTMOBILE_ENABLE_ANALYTICS_ADV</code> para consultar reportes avanzados.
          </p>
        </section>
      )}
    </div>
  );
}

export default AnalyticsPage;

