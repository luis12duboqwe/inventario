import React, { useEffect, useState, useCallback } from "react";
import { SummaryCards } from "../components/common";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import { emitClientError } from "../../../utils/clientLog";
import {
  getAnalyticsRealtime,
  getSalesProjectionAnalytics,
  getRotationAnalytics,
} from "@api/analytics";
import { listReturns } from "@api/sales";

export default function SalesDashboardPage() {
  const { token, formatCurrency, pushToast } = useDashboard();
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState({
    salesToday: 0,
    averageTicket: 0,
    topProduct: "—",
    returnsToday: 0,
  });

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const today = new Date().toISOString().split("T")[0] ?? "";

      const [realtime, projection, rotation, returns] = await Promise.all([
        getAnalyticsRealtime(token),
        getSalesProjectionAnalytics(token),
        getRotationAnalytics(token),
        listReturns(token, { dateFrom: today, dateTo: today }),
      ]);

      // 1. Ventas hoy (Sum of sales_today from all stores)
      const salesToday = realtime.items.reduce((acc, item) => acc + (item.sales_today || 0), 0);

      // 2. Ticket promedio (Average of average_ticket from all stores)
      const validTickets = projection.items.filter((p) => p.average_ticket > 0);
      const averageTicket =
        validTickets.length > 0
          ? validTickets.reduce((acc, item) => acc + item.average_ticket, 0) / validTickets.length
          : 0;

      // 3. Top producto (Best selling item from rotation analytics)
      const topItem =
        rotation.items.length > 0
          ? rotation.items.reduce(
              (prev, current) => (prev.sold_units > current.sold_units ? prev : current),
              rotation.items[0]!,
            )
          : null;
      const topProduct = topItem ? topItem.name : "—";

      // 4. Devoluciones hoy (Count of returns)
      const returnsToday = returns.totals.total || returns.items.length;

      setMetrics({
        salesToday,
        averageTicket,
        topProduct,
        returnsToday,
      });
    } catch (err) {
      emitClientError("SalesDashboardPage", "Error loading sales dashboard", err);
      pushToast("Error al cargar métricas de ventas", "error");
    } finally {
      setLoading(false);
    }
  }, [token, pushToast]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const cards = [
    {
      label: "Ventas hoy",
      value: loading ? "..." : formatCurrency(metrics.salesToday),
    },
    {
      label: "Ticket promedio",
      value: loading ? "..." : formatCurrency(metrics.averageTicket),
    },
    {
      label: "Top producto",
      value: loading ? "..." : metrics.topProduct,
    },
    {
      label: "Devoluciones hoy",
      value: loading ? "..." : metrics.returnsToday.toString(),
    },
  ];

  return (
    <div className="sales-dashboard-grid">
      <SummaryCards items={cards} />
    </div>
  );
}
