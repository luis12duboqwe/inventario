// [PACK29-*] Página principal de reportes de ventas
import { useCallback, useEffect, useMemo, useState } from "react";
import { BarChart3 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import ModuleHeader from "@/shared/components/ModuleHeader";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import { useReportsModule } from "../hooks/useReportsModule";
import SalesReportsFilters from "../components/SalesReportsFilters";
import SalesKpiGrid from "../components/SalesKpiGrid";
import TopProductsTable from "../components/TopProductsTable";
import type { SalesKpiGridProps } from "../components/SalesKpiGrid";
import type { TopProductsTableProps } from "../components/TopProductsTable";
import {
  fetchCashCloseReport,
  fetchSalesByProduct,
  fetchSalesSummary,
  type CashCloseReport,
  type SalesByProductItem,
  type SalesSummaryReport,
  type SalesReportFilters,
} from "@api/reports";
import { downloadText } from "@/lib/download";
import { toCsv } from "@/lib/csv";

export type SalesFiltersState = {
  from: string | null;
  to: string | null;
  branchId: number | null;
};

const ONE_DAY = 24 * 60 * 60 * 1000;

function resolveDefaultFilters(): SalesFiltersState {
  const today = new Date();
  const sevenDaysAgo = new Date(today.getTime() - 6 * ONE_DAY);
  return {
    from: sevenDaysAgo.toISOString().slice(0, 10),
    to: today.toISOString().slice(0, 10),
    branchId: null,
  };
}

function SalesReportsPage() {
  const dashboard = useDashboard();
  const { pushToast, formatCurrency } = useReportsModule();
  const [filters, setFilters] = useState<SalesFiltersState>(() => resolveDefaultFilters());

  const availableStores = dashboard.stores;
  const enableAnalytics = dashboard.enableAnalyticsAdv;

  const appliedFilters = useMemo(() => filters, [filters]);

  const summaryQuery = useQuery<SalesSummaryReport>({
    queryKey: ["reports", "sales", "summary", appliedFilters],
    queryFn: () => {
      const payload: SalesReportFilters = {};
      if (appliedFilters.from) payload.from = appliedFilters.from;
      if (appliedFilters.to) payload.to = appliedFilters.to;
      if (typeof appliedFilters.branchId === "number") payload.branchId = appliedFilters.branchId;
      return fetchSalesSummary(payload);
    },
    enabled: enableAnalytics,
    staleTime: ONE_DAY,
  });

  const productsQuery = useQuery<SalesByProductItem[]>({
    queryKey: ["reports", "sales", "products", appliedFilters],
    queryFn: () => {
      const payload: SalesReportFilters = { limit: 20 };
      if (appliedFilters.from) payload.from = appliedFilters.from;
      if (appliedFilters.to) payload.to = appliedFilters.to;
      if (typeof appliedFilters.branchId === "number") payload.branchId = appliedFilters.branchId;
      return fetchSalesByProduct(payload);
    },
    enabled: enableAnalytics,
    staleTime: ONE_DAY,
  });

  const cashDate = useMemo(() => appliedFilters.to ?? appliedFilters.from, [appliedFilters.from, appliedFilters.to]);

  const cashCloseQuery = useQuery<CashCloseReport>({
    queryKey: ["reports", "sales", "cash", cashDate, appliedFilters.branchId],
    queryFn: () => {
      const payload: { date: string; branchId?: number } = {
        date: cashDate ?? new Date().toISOString().slice(0, 10),
      };
      if (typeof appliedFilters.branchId === "number") {
        payload.branchId = appliedFilters.branchId;
      }
      return fetchCashCloseReport(payload);
    },
    enabled: enableAnalytics,
    staleTime: ONE_DAY,
  });

  useEffect(() => {
    if (summaryQuery.error) {
      pushToast({ message: "No fue posible cargar el resumen de ventas", variant: "error" });
    }
  }, [summaryQuery.error, pushToast]);

  useEffect(() => {
    if (productsQuery.error) {
      pushToast({ message: "No fue posible cargar el top de productos", variant: "error" });
    }
  }, [productsQuery.error, pushToast]);

  useEffect(() => {
    if (cashCloseQuery.error) {
      pushToast({ message: "No fue posible calcular el cierre sugerido", variant: "error" });
    }
  }, [cashCloseQuery.error, pushToast]);

  const handleFiltersChange = useCallback((next: SalesFiltersState) => {
    if (next.from && next.to && next.from > next.to) {
      setFilters({ ...next, to: next.from });
      return;
    }
    setFilters(next);
  }, []);

  const handleRefresh = useCallback(() => {
    summaryQuery.refetch();
    productsQuery.refetch();
    cashCloseQuery.refetch();
  }, [cashCloseQuery, productsQuery, summaryQuery]);

  const handleExport = useCallback(() => {
    const products = productsQuery.data;
    if (!products || products.length === 0) {
      pushToast({ message: "No hay productos para exportar", variant: "info" });
      return;
    }
    const csv = toCsv(products, [
      { key: "sku", title: "SKU" },
      { key: "name", title: "Producto" },
      { key: "qty", title: "Cantidad" },
      {
        key: "gross",
        title: "Ventas brutas",
        map: (value) => formatCurrency(Number(value) || 0),
      },
      {
        key: "net",
        title: "Ventas netas",
        map: (value) => formatCurrency(Number(value) || 0),
      },
    ]);
    const rangeLabel = [appliedFilters.from, appliedFilters.to]
      .filter(Boolean)
      .join("_al_")
      .replace(/:/g, "-");
    const filename = rangeLabel ? `top-productos_${rangeLabel}.csv` : "top-productos.csv";
    downloadText(csv, filename, "text/csv;charset=utf-8");
  }, [appliedFilters.from, appliedFilters.to, formatCurrency, productsQuery.data, pushToast]);

  if (!enableAnalytics) {
    return (
      <div className="module-content">
        <ModuleHeader
          icon={<BarChart3 aria-hidden="true" />}
          title="Reportes de ventas"
          subtitle="Explora métricas operativas, top de productos y arqueos sugeridos."
          status="warning"
          statusLabel="Analítica avanzada inactiva"
        />
        <section className="card">
          <h2>Activa analítica avanzada</h2>
          <p className="muted-text">
            Habilita la variable corporativa <code>SOFTMOBILE_ENABLE_ANALYTICS_ADV</code> para consultar estos reportes.
          </p>
        </section>
      </div>
    );
  }

  return (
    <div className="module-content">
      <ModuleHeader
        icon={<BarChart3 aria-hidden="true" />}
        title="Reportes de ventas"
        subtitle="Ventas consolidadas, devoluciones y cierre sugerido por sucursal."
        status="ok"
        statusLabel="Analítica avanzada activa"
      />
      <SalesReportsFilters
        filters={appliedFilters}
        stores={availableStores}
        onFiltersChange={handleFiltersChange}
        onRefresh={handleRefresh}
        onExport={handleExport}
        loading={summaryQuery.isFetching || productsQuery.isFetching || cashCloseQuery.isFetching}
        exportDisabled={!productsQuery.data || productsQuery.data.length === 0}
      />
      {(() => {
        const props: SalesKpiGridProps = {
          loading: summaryQuery.isFetching || cashCloseQuery.isFetching,
          formatCurrency,
        };
        if (summaryQuery.data) {
          props.summary = summaryQuery.data;
        }
        if (cashCloseQuery.data) {
          props.cashClose = cashCloseQuery.data;
        }
        return <SalesKpiGrid {...props} />;
      })()}
      {(() => {
        const props: TopProductsTableProps = {
          isLoading: productsQuery.isFetching,
          formatCurrency,
        };
        if (productsQuery.data) {
          props.products = productsQuery.data;
        }
        return <TopProductsTable {...props} />;
      })()}
    </div>
  );
}

export default SalesReportsPage;
