import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useDashboard } from "./DashboardContext";

const PIE_COLORS = ["#06b6d4", "#22d3ee", "#38bdf8", "#0ea5e9", "#0891b2"];

function resolveStatusTone(value: number, threshold: number, inverse = false): "good" | "alert" | "info" {
  if (inverse) {
    return value <= threshold ? "good" : "alert";
  }
  return value >= threshold ? "good" : "alert";
}

function GlobalMetrics() {
  const { metrics, formatCurrency } = useDashboard();

  if (!metrics) {
    return null;
  }

  const performance = metrics.global_performance;
  const cards = [
    {
      id: "sales",
      title: "Ventas netas",
      value: formatCurrency(performance.total_sales),
      caption: `${performance.sales_count} operaciones cerradas`,
      tone: resolveStatusTone(performance.total_sales, 1),
    },
    {
      id: "profit",
      title: "Ganancia bruta",
      value: formatCurrency(performance.gross_profit),
      caption: performance.gross_profit >= 0 ? "Margen positivo" : "Atiende descuentos excesivos",
      tone: resolveStatusTone(performance.gross_profit, 0),
    },
    {
      id: "stock",
      title: "Inventario total",
      value: `${performance.total_stock.toLocaleString("es-MX")} uds`,
      caption: "Unidades disponibles en tiendas",
      tone: "info" as const,
    },
    {
      id: "repairs",
      title: "Reparaciones abiertas",
      value: `${performance.open_repairs}`,
      caption: performance.open_repairs === 0 ? "Sin pendientes" : "Coordina cierres con taller",
      tone: resolveStatusTone(performance.open_repairs, 0, true),
    },
  ];

  const salesTrend = metrics.sales_trend.map((entry) => ({ ...entry, value: Number(entry.value.toFixed(2)) }));
  const stockBreakdown = metrics.stock_breakdown;
  const profitSlices = metrics.profit_breakdown.length > 0 ? metrics.profit_breakdown : metrics.stock_breakdown;
  const repairMix = metrics.repair_mix;

  return (
    <section className="global-metrics">
      <div className="metric-cards" aria-label="Tarjetas de desempeño global">
        {cards.map((card) => (
          <article key={card.id} className={`metric-card metric-${card.tone}`}>
            <h3>{card.title}</h3>
            <p className="metric-value">{card.value}</p>
            <p className="metric-caption">{card.caption}</p>
          </article>
        ))}
      </div>

      <div className="metric-charts">
        <article className="chart-card">
          <header>
            <h3>Tendencia de ventas</h3>
            <span className="chart-caption">Últimos 7 días</span>
          </header>
          {salesTrend.length === 0 ? (
            <p className="muted-text">Aún no hay datos de ventas recientes.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={salesTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
                <XAxis dataKey="label" stroke="var(--text-secondary)" />
                <YAxis stroke="var(--text-secondary)" tickFormatter={(value) => formatCurrency(value).replace("MX$", "")} />
                <Tooltip formatter={(value: number) => formatCurrency(value)} />
                <Legend />
                <Line type="monotone" dataKey="value" stroke="#06b6d4" strokeWidth={2} dot={{ r: 3 }} name="Ventas" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </article>

        <article className="chart-card">
          <header>
            <h3>Inventario por tienda</h3>
            <span className="chart-caption">Unidades registradas</span>
          </header>
          {stockBreakdown.length === 0 ? (
            <p className="muted-text">No hay tiendas registradas.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={stockBreakdown}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
                <XAxis dataKey="label" stroke="var(--text-secondary)" />
                <YAxis stroke="var(--text-secondary)" />
                <Tooltip />
                <Legend />
                <Bar dataKey="value" fill="#1d4ed8" name="Unidades" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </article>

        <article className="chart-card">
          <header>
            <h3>Distribución de ganancias</h3>
            <span className="chart-caption">Participación por tienda</span>
          </header>
          {profitSlices.length === 0 ? (
            <p className="muted-text">No hay registros de ganancias para graficar.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Tooltip formatter={(value: number) => formatCurrency(value)} />
                <Legend />
                <Pie data={profitSlices} dataKey="value" nameKey="label" innerRadius={60} outerRadius={90} paddingAngle={4}>
                  {profitSlices.map((entry, index) => (
                    <Cell key={entry.label} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          )}
        </article>

        <article className="chart-card">
          <header>
            <h3>Estado de reparaciones</h3>
            <span className="chart-caption">Resumen global</span>
          </header>
          {repairMix.length === 0 ? (
            <p className="muted-text">Sin órdenes de reparación registradas.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={repairMix}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
                <XAxis dataKey="label" stroke="var(--text-secondary)" />
                <YAxis stroke="var(--text-secondary)" />
                <Tooltip />
                <Legend />
                <Bar dataKey="value" fill="#22d3ee" name="Órdenes" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </article>
      </div>
    </section>
  );
}

export default GlobalMetrics;
