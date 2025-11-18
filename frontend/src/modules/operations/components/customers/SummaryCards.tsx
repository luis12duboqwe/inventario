import type {
  CustomerDashboardMetrics,
  CustomerPortfolioItem,
  CustomerPortfolioReport,
} from "../../../../api";
import { colors } from "../../../../theme/designTokens";
import type {
  DashboardFilters,
  PortfolioFilters,
} from "../../../../types/customers";

type CustomersSummaryCardsProps = {
  portfolio: CustomerPortfolioReport | null;
  portfolioLoading: boolean;
  portfolioError: string | null;
  portfolioFilters: PortfolioFilters;
  dashboardMetrics: CustomerDashboardMetrics | null;
  dashboardLoading: boolean;
  dashboardError: string | null;
  dashboardFilters: DashboardFilters;
  delinquentRatio: { percentage: number; total: number };
  formatCurrency: (value: number) => string;
  onPortfolioFiltersChange: <Field extends keyof PortfolioFilters>(
    field: Field,
    value: PortfolioFilters[Field],
  ) => void;
  refreshPortfolio: () => void;
  onExportPortfolio: (format: "pdf" | "xlsx") => void;
  onDashboardFiltersChange: <Field extends keyof DashboardFilters>(
    field: Field,
    value: DashboardFilters[Field],
  ) => void;
  refreshDashboard: () => void;
  exportingPortfolio: "pdf" | "xlsx" | null;
};

const CustomersSummaryCards = ({
  portfolio,
  portfolioLoading,
  portfolioError,
  portfolioFilters,
  dashboardMetrics,
  dashboardLoading,
  dashboardError,
  dashboardFilters,
  delinquentRatio,
  formatCurrency,
  onPortfolioFiltersChange,
  refreshPortfolio,
  onExportPortfolio,
  onDashboardFiltersChange,
  refreshDashboard,
  exportingPortfolio,
}: CustomersSummaryCardsProps) => {
  const newCustomersMaxValue = dashboardMetrics
    ? Math.max(...dashboardMetrics.new_customers_per_month.map((point) => point.value), 0)
    : 0;

  return (
    <div className="customers-dashboard">
      <div className="card">
        <div className="card-header">
          <div>
            <h3>Portafolio de clientes</h3>
            <p className="muted-text">
              Identifica clientes morosos o compradores frecuentes y exporta el reporte oficial con estilo oscuro.
            </p>
          </div>
          <div className="report-actions">
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => onExportPortfolio("pdf")}
              disabled={exportingPortfolio === "pdf"}
            >
              {exportingPortfolio === "pdf" ? "Generando..." : "Exportar PDF"}
            </button>
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => onExportPortfolio("xlsx")}
              disabled={exportingPortfolio === "xlsx"}
            >
              {exportingPortfolio === "xlsx" ? "Generando..." : "Exportar Excel"}
            </button>
          </div>
        </div>

        <div className="form-grid">
          <label>
            Categoría
            <select
              value={portfolioFilters.category}
              onChange={(event) =>
                onPortfolioFiltersChange(
                  "category",
                  event.target.value as PortfolioFilters["category"],
                )
              }
            >
              <option value="delinquent">Clientes morosos</option>
              <option value="frequent">Compradores frecuentes</option>
            </select>
          </label>
          <label>
            Límite
            <input
              type="number"
              min={1}
              max={100}
              value={portfolioFilters.limit}
              onChange={(event) =>
                onPortfolioFiltersChange("limit", Number(event.target.value) || portfolioFilters.limit)
              }
            />
          </label>
          <label>
            Desde
            <input
              type="date"
              value={portfolioFilters.dateFrom}
              onChange={(event) => onPortfolioFiltersChange("dateFrom", event.target.value)}
            />
          </label>
          <label>
            Hasta
            <input
              type="date"
              value={portfolioFilters.dateTo}
              onChange={(event) => onPortfolioFiltersChange("dateTo", event.target.value)}
            />
          </label>
          <div>
            <button
              type="button"
              className="btn btn--ghost"
              onClick={refreshPortfolio}
              disabled={portfolioLoading}
            >
              {portfolioLoading ? "Actualizando..." : "Actualizar vista"}
            </button>
          </div>
        </div>

        {portfolioLoading ? (
          <p className="muted-text">Generando portafolio...</p>
        ) : portfolioError ? (
          <p className="error-text">{portfolioError}</p>
        ) : portfolio ? (
          <>
            <div className="portfolio-summary">
              <div>
                <span className="muted-text">Clientes listados</span>
                <strong>{portfolio.totals.customers}</strong>
              </div>
              <div>
                <span className="muted-text">Deuda total</span>
                <strong>${formatCurrency(portfolio.totals.outstanding_debt)}</strong>
              </div>
              <div>
                <span className="muted-text">Ventas acumuladas</span>
                <strong>${formatCurrency(portfolio.totals.sales_total)}</strong>
              </div>
            </div>
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Cliente</th>
                    <th>Tipo</th>
                    <th>Estado</th>
                    <th>Saldo</th>
                    <th>Ventas</th>
                    <th>Última compra</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio.items.map((item: CustomerPortfolioItem) => (
                    <tr key={item.customer_id}>
                      <td>
                        <strong>{item.name}</strong>
                        <div className="muted-text">#{item.customer_id}</div>
                      </td>
                      <td>{item.customer_type}</td>
                      <td>{item.status}</td>
                      <td>${formatCurrency(item.outstanding_debt)}</td>
                      <td>
                        ${formatCurrency(item.sales_total)} ({item.sales_count} ventas)
                      </td>
                      <td>
                        {item.last_sale_at
                          ? new Date(item.last_sale_at).toLocaleDateString("es-HN")
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p className="muted-text">
            Configura los filtros y presiona «Actualizar vista» para consultar el portafolio.
          </p>
        )}
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <h3>Dashboard de clientes</h3>
            <p className="muted-text">
              Visualiza las altas mensuales, el top de compradores y el porcentaje de morosos.
            </p>
          </div>
          <div className="report-actions">
            <label>
              Meses
              <input
                type="number"
                min={1}
                max={24}
                value={dashboardFilters.months}
                onChange={(event) =>
                  onDashboardFiltersChange("months", Math.max(1, Number(event.target.value)))
                }
              />
            </label>
            <label>
              Top
              <input
                type="number"
                min={1}
                max={20}
                value={dashboardFilters.topLimit}
                onChange={(event) =>
                  onDashboardFiltersChange("topLimit", Math.max(1, Number(event.target.value)))
                }
              />
            </label>
            <button
              type="button"
              className="btn btn--ghost"
              onClick={refreshDashboard}
              disabled={dashboardLoading}
            >
              {dashboardLoading ? "Actualizando..." : "Actualizar"}
            </button>
          </div>
        </div>

        {dashboardLoading ? (
          <p className="muted-text">Cargando métricas...</p>
        ) : dashboardError ? (
          <p className="error-text">{dashboardError}</p>
        ) : dashboardMetrics ? (
          <div className="dashboard-grid">
            <div className="dashboard-card">
              <h4>Clientes nuevos por mes</h4>
              {dashboardMetrics.new_customers_per_month.length === 0 ? (
                <p className="muted-text">Sin registros en el rango indicado.</p>
              ) : (
                <ul className="bars-list">
                  {dashboardMetrics.new_customers_per_month.map((point) => {
                    const normalizedWidth =
                      newCustomersMaxValue > 0
                        ? point.value > 0
                          ? Math.max(
                              8,
                              Math.min(100, Math.round((point.value / newCustomersMaxValue) * 100)),
                            )
                          : 0
                        : 0;
                    return (
                      <li key={point.label}>
                        <span>{point.label}</span>
                        <div className="bar">
                          <div
                            className="bar__fill"
                            style={{ width: `${normalizedWidth}%` }}
                          />
                          <span className="bar__value">{point.value}</span>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>

            <div className="dashboard-card">
              <h4>Top compradores</h4>
              {dashboardMetrics.top_customers.length === 0 ? (
                <p className="muted-text">No hay ventas registradas.</p>
              ) : (
                <ul className="summary-list">
                  {dashboardMetrics.top_customers.map((customer) => (
                    <li key={customer.customer_id}>
                      <div>
                        <strong>{customer.name}</strong>
                        <span className="muted-text">
                          {customer.sales_count} ventas · ${formatCurrency(customer.sales_total)}
                        </span>
                      </div>
                      <span className="summary-amount">
                        Deuda ${formatCurrency(customer.outstanding_debt)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="dashboard-card">
              <h4>Morosidad</h4>
              <div className="morosity-indicator">
                <div className="morosity-ring">
                  <div
                    className="morosity-ring__fill"
                    style={{
                      background: `conic-gradient(${colors.accent} 0% ${delinquentRatio.percentage}%, ${colors.accentSoft} ${delinquentRatio.percentage}% 100%)`,
                    }}
                  />
                  <span>{delinquentRatio.percentage}%</span>
                </div>
                <div>
                  <p className="muted-text">Clientes morosos identificados</p>
                  <strong>${formatCurrency(delinquentRatio.total)}</strong>
                  <p className="muted-text">Saldo vencido total</p>
                </div>
              </div>
              <p className="muted-text small">
                Datos generados el {dashboardMetrics.generated_at
                  ? new Date(dashboardMetrics.generated_at).toLocaleString("es-HN")
                  : "—"}.
              </p>
            </div>
          </div>
        ) : (
          <p className="muted-text">Configura los filtros y presiona actualizar para ver las métricas.</p>
        )}
      </div>
    </div>
  );
};

export default CustomersSummaryCards;
