// [PACK29-*] Tarjetas KPI para el resumen de ventas
import type { SalesSummaryReport, CashCloseReport } from "@api/reports";

export type SalesKpiGridProps = {
  summary?: SalesSummaryReport;
  cashClose?: CashCloseReport;
  loading?: boolean;
  formatCurrency: (value: number) => string;
};

function SalesKpiGrid({ summary, cashClose, loading = false, formatCurrency }: SalesKpiGridProps) {
  if (loading && !summary && !cashClose) {
    return (
      <section className="sales-kpi-grid" aria-busy="true" aria-live="polite">
        <article className="card sales-kpi-card">
          <div className="loading-overlay compact">
            <span className="spinner" aria-hidden="true" />
            <span>Cargando métricas…</span>
          </div>
        </article>
      </section>
    );
  }

  const totalSales = summary?.totalSales ?? 0;
  const avgTicket = summary?.avgTicket ?? 0;
  const totalOrders = summary?.totalOrders ?? 0;
  const returnsCount = summary?.returnsCount ?? 0;
  const netSales = summary?.net ?? 0;
  const closingSuggested = cashClose?.closingSuggested ?? 0;
  const refunds = cashClose?.refunds ?? 0;

  return (
    <section className="sales-kpi-grid" aria-label="Resumen de ventas">
      <article className="card sales-kpi-card" role="group" aria-label="Ventas brutas">
        <h3>Ventas brutas</h3>
        <p className="sales-kpi-value">{formatCurrency(totalSales)}</p>
        <p className="muted-text">Órdenes registradas: {totalOrders}</p>
      </article>
      <article className="card sales-kpi-card" role="group" aria-label="Ticket promedio">
        <h3>Ticket promedio</h3>
        <p className="sales-kpi-value">{formatCurrency(avgTicket)}</p>
        <p className="muted-text">Devoluciones registradas: {returnsCount}</p>
      </article>
      <article className="card sales-kpi-card" role="group" aria-label="Cierre sugerido">
        <h3>Cierre sugerido</h3>
        <p className="sales-kpi-value">{formatCurrency(closingSuggested)}</p>
        <p className="muted-text">Reembolsos del día: {formatCurrency(refunds)}</p>
        <p className="muted-text">Ventas netas: {formatCurrency(netSales)}</p>
      </article>
    </section>
  );
}

export default SalesKpiGrid;
