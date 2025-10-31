import type { PurchaseStatistics } from "../../../../api";

type PurchasesSummaryCardsProps = {
  statistics: PurchaseStatistics | null;
  loading: boolean;
  currencyFormatter: Intl.NumberFormat;
};

const PurchasesSummaryCards = ({ statistics, loading, currencyFormatter }: PurchasesSummaryCardsProps) => {
  if (loading) {
    return <p className="muted-text">Calculando estadísticas…</p>;
  }

  if (!statistics) {
    return <p className="muted-text">Sin métricas disponibles.</p>;
  }

  return (
    <div className="stats-grid">
      <div className="metric-card">
        <h3>Total invertido</h3>
        <p className="metric-primary">{currencyFormatter.format(statistics.total)}</p>
        <p className="metric-secondary">Impuestos: {currencyFormatter.format(statistics.impuesto)}</p>
      </div>
      <div className="metric-card">
        <h3>Órdenes registradas</h3>
        <p className="metric-primary">{statistics.compras_registradas}</p>
      </div>
      <div className="metric-card">
        <h3>Proveedores frecuentes</h3>
        <ul className="compact-list">
          {statistics.top_vendors.length === 0 ? (
            <li className="muted-text">Sin datos disponibles</li>
          ) : (
            statistics.top_vendors.map((item) => (
              <li key={item.vendor_id}>
                {item.vendor_name} · {currencyFormatter.format(item.total)} ({item.orders} órdenes)
              </li>
            ))
          )}
        </ul>
      </div>
      <div className="metric-card">
        <h3>Usuarios con más compras</h3>
        <ul className="compact-list">
          {statistics.top_users.length === 0 ? (
            <li className="muted-text">Sin datos disponibles</li>
          ) : (
            statistics.top_users.map((item) => (
              <li key={item.user_id}>
                {(item.user_name || `Usuario #${item.user_id}`) + " · "}
                {currencyFormatter.format(item.total)} ({item.orders} órdenes)
              </li>
            ))
          )}
        </ul>
      </div>
      <div className="metric-card form-span">
        <h3>Totales mensuales</h3>
        <ul className="compact-list">
          {statistics.monthly_totals.length === 0 ? (
            <li className="muted-text">Sin registros recientes</li>
          ) : (
            statistics.monthly_totals.map((point) => (
              <li key={point.label}>
                {point.label}: {currencyFormatter.format(point.value)}
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
};

export default PurchasesSummaryCards;
