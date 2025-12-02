import type { SalesDashboard } from "./types";

type Props = {
  dashboard: SalesDashboard;
  formatCurrency: (value: number) => string;
};

function SummaryCards({ dashboard, formatCurrency }: Props) {
  return (
    <div className="section-divider">
      <h3>Resumen diario</h3>
      {dashboard.count === 0 ? (
        <p className="muted-text">Aún no hay ventas registradas para mostrar estadísticas.</p>
      ) : (
        <div className="metric-cards">
          <article className="metric-card metric-info">
            <h4>Ventas netas</h4>
            <p className="metric-value">{formatCurrency(dashboard.total)}</p>
            <p className="metric-caption">{dashboard.count} operaciones registradas</p>
          </article>
          <article className="metric-card metric-secondary">
            <h4>Impuestos generados</h4>
            <p className="metric-value">{formatCurrency(dashboard.tax)}</p>
            <p className="metric-caption">Subtotal {formatCurrency(dashboard.subtotal)}</p>
          </article>
          <article className="metric-card metric-primary">
            <h4>Ticket promedio</h4>
            <p className="metric-value">{formatCurrency(dashboard.average)}</p>
            <p className="metric-caption">Calculado sobre {dashboard.count} ventas</p>
          </article>
        </div>
      )}
      {dashboard.dailyStats.length > 0 ? (
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th>Día</th>
                <th>Total vendido</th>
                <th>Operaciones</th>
                <th>Ticket promedio</th>
              </tr>
            </thead>
            <tbody>
              {dashboard.dailyStats.map((entry) => (
                <tr key={entry.day}>
                  <td>{entry.day}</td>
                  <td>{formatCurrency(entry.total)}</td>
                  <td>{entry.count}</td>
                  <td>{formatCurrency(entry.average)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

export default SummaryCards;
