import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, beforeEach, expect, it, vi } from "vitest";
import GlobalMetrics from "../GlobalMetrics";
import type { DashboardAuditAlerts, InventoryMetrics } from "../../../../api";

type DashboardStub = {
  enablePriceLists: boolean;
  metrics: InventoryMetrics | null;
  formatCurrency: (value: number) => string;
  loading: boolean;
};

const dashboardState: DashboardStub = {
  enablePriceLists: false,
  metrics: null,
  formatCurrency: (value: number) =>
    new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" }).format(value),
  loading: false,
};

vi.mock("../../context/DashboardContext", () => ({
  useDashboard: () => dashboardState,
}));

const sampleMetrics: InventoryMetrics = {
  totals: { stores: 3, devices: 120, total_units: 340, total_value: 850000 },
  top_stores: [],
  low_stock_devices: [],
  global_performance: {
    total_sales: 125000,
    sales_count: 18,
    total_stock: 340,
    open_repairs: 3,
    gross_profit: 28000,
  },
  accounts_receivable: {
    total_outstanding_debt: 18000,
    customers_with_debt: 3,
    moroso_flagged: 1,
    top_debtors: [
      { customer_id: 301, name: "Cliente con mora", outstanding_debt: 12000, available_credit: 5000 },
      { customer_id: 302, name: "Cliente al día", outstanding_debt: 6000, available_credit: null },
    ],
  },
  sales_insights: {
    average_ticket: 6944.44,
    top_products: [
      { label: "Galaxy S24", value: 52000, quantity: 4 },
      { label: "iPhone 15 Pro", value: 43000, quantity: 3 },
    ],
    top_customers: [
      { label: "Cliente Corporativo", value: 65000, quantity: 3 },
      { label: "Empresa Norte", value: 42000, quantity: 2 },
    ],
    payment_mix: [
      { label: "Crédito", value: 72000, percentage: 58.06 },
      { label: "Contado", value: 52000, percentage: 41.94 },
    ],
  },
  sales_trend: [
    { label: "Lun", value: 22000 },
    { label: "Mar", value: 19500 },
  ],
  stock_breakdown: [
    { label: "Centro", value: 180 },
    { label: "Norte", value: 160 },
  ],
  repair_mix: [],
  profit_breakdown: [
    { label: "Centro", value: 65 },
    { label: "Norte", value: 35 },
  ],
  audit_alerts: {
    total: 3,
    critical: 1,
    warning: 1,
    info: 1,
    has_alerts: true,
    pending_count: 2,
    acknowledged_count: 1,
    highlights: [
      {
        id: 15,
        action: "sync_outbox_pending",
        created_at: "2025-02-28T08:35:00.000Z",
        severity: "critical",
        entity_type: "sync_outbox",
        entity_id: "88",
        status: "pending",
        acknowledged_at: null,
        acknowledged_by_name: null,
        acknowledged_note: null,
      },
    ],
    acknowledged_entities: [
      {
        entity_type: "pos_sale",
        entity_id: "2002",
        acknowledged_at: "2025-02-28T07:45:00.000Z",
        acknowledged_by_name: "Admin Seguridad",
        note: "Se revirtió la venta duplicada",
      },
      {
        entity_type: "transfer_order",
        entity_id: "301",
        acknowledged_at: "2025-02-27T22:15:00.000Z",
        acknowledged_by_name: "Soporte QA",
        note: "Confirmación por teléfono",
      },
    ],
  },
};

const auditAlertsMock: DashboardAuditAlerts = {
  total: 4,
  critical: 1,
  warning: 2,
  info: 1,
  has_alerts: true,
  pending_count: 3,
  acknowledged_count: 1,
  highlights: [
    {
      id: "sync-1",
      action: "sync_outbox_backlog",
      created_at: "2025-03-01T09:20:00.000Z",
      severity: "warning",
      entity_type: "sync_outbox",
      entity_id: "101",
    },
  ],
  acknowledged_entities: [
    {
      entity_type: "audit_log",
      entity_id: "9001",
      acknowledged_at: "2025-03-01T07:00:00.000Z",
      acknowledged_by_name: "Seguridad", // [PACK36-tests]
      note: "Revisión preliminar",
    },
  ],
};

describe("GlobalMetrics", () => {
  beforeEach(() => {
    dashboardState.metrics = sampleMetrics;
    dashboardState.loading = false;
  });

  it("presenta resumen de alertas y acceso rápido a Seguridad", () => {
    render(
      <MemoryRouter>
        <GlobalMetrics />
      </MemoryRouter>
    );

    expect(screen.getByText(/2 pendientes · 1 atendidas/i)).toBeInTheDocument();
    expect(screen.getByText(/Último acuse:/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Abrir módulo de Seguridad/i })).toHaveAttribute(
      "href",
      "/dashboard/security"
    );
    expect(screen.getByText(/Cartera por cobrar/i)).toBeInTheDocument();
    expect(screen.getByText(/Cliente con mora/i)).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes("6,944.44"))).toBeInTheDocument();
    expect(screen.getByText(/Cliente Corporativo/i)).toBeInTheDocument();
  });

  it("muestra estado vacío cuando no hay métricas disponibles", () => {
    // [PACK36-tests]
    dashboardState.metrics = null;
    dashboardState.loading = false;
    const { container } = render(
      <MemoryRouter>
        <GlobalMetrics auditAlertsMock={auditAlertsMock} />
      </MemoryRouter>
    );

    expect(screen.getByText(/Sin métricas disponibles por el momento/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Abrir módulo de Seguridad/i })).toHaveAttribute(
      "href",
      "/dashboard/security"
    );
    expect(screen.getByText(/Existen 3 alertas pendientes en Seguridad/i)).toBeInTheDocument();
    expect(container.querySelector(".metric-empty")).not.toBeNull();
  });

  it("renderiza skeleton de carga mientras se solicitan métricas", () => {
    // [PACK36-tests]
    dashboardState.metrics = null;
    dashboardState.loading = true;
    const { container } = render(
      <MemoryRouter>
        <GlobalMetrics />
      </MemoryRouter>
    );

    const busyElements = container.querySelectorAll("[aria-busy='true']");
    expect(busyElements.length).toBeGreaterThan(0);
    expect(container.querySelectorAll(".metric-card").length).toBeGreaterThan(0);
  });
});
