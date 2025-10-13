import AnalyticsBoard from "../AnalyticsBoard";
import { useDashboard } from "./DashboardContext";

function AnalyticsSection() {
  const { token, enableAnalyticsAdv } = useDashboard();

  if (!enableAnalyticsAdv) {
    return (
      <section className="card">
        <h2>Analítica avanzada</h2>
        <p className="muted-text">
          Activa el flag corporativo <code>SOFTMOBILE_ENABLE_ANALYTICS_ADV</code> para consultar reportes avanzados.
        </p>
      </section>
    );
  }

  return <AnalyticsBoard token={token} />;
}

export default AnalyticsSection;

