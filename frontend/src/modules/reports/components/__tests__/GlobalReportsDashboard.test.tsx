import { render, screen, waitFor } from "@testing-library/react";
import { type ReactNode } from "react";
import { describe, beforeEach, expect, it, vi, type Mock } from "vitest";

import {
  getGlobalReportOverview,
  getGlobalReportDashboard,
  type GlobalReportOverview,
  type GlobalReportDashboard,
} from "../../../../api";
import GlobalReportsDashboard from "../GlobalReportsDashboard";

type ReportsModuleStub = {
  token: string;
  pushToast: (message: { message: string; variant: "success" | "error" | "info" }) => void;
};

const moduleStub: ReportsModuleStub = {
  token: "token-prueba",
  pushToast: vi.fn(),
};

vi.mock("../../hooks/useReportsModule", () => ({
  useReportsModule: () => moduleStub,
}));

vi.mock("../../../../api", async (original) => {
  const actual = await original();
  return {
    ...actual,
    getGlobalReportOverview: vi.fn(),
    getGlobalReportDashboard: vi.fn(),
    downloadGlobalReportPdf: vi.fn(),
    downloadGlobalReportXlsx: vi.fn(),
    downloadGlobalReportCsv: vi.fn(),
  };
});

vi.mock("../../../../shared/components/ScrollableTable", () => ({
  __esModule: true,
  default: ({ children }: { children: ReactNode }) => <div data-testid="scrollable-table">{children}</div>,
}));

vi.mock("../../../../utils/corporateReason", () => ({
  promptCorporateReason: () => "Motivo corporativo de prueba",
}));

const overviewSample: GlobalReportOverview = {
  generated_at: "2025-10-29T10:30:00Z",
  filters: { date_from: null, date_to: null, module: null, severity: null },
  totals: {
    logs: 8,
    errors: 2,
    info: 3,
    warning: 2,
    error: 1,
    critical: 2,
    sync_pending: 5,
    sync_failed: 1,
    last_activity_at: "2025-10-29T10:00:00Z",
  },
  module_breakdown: [
    { name: "inventario", total: 4 },
    { name: "sincronizacion", total: 4 },
  ],
  severity_breakdown: [
    { name: "info", total: 3 },
    { name: "warning", total: 2 },
    { name: "error", total: 1 },
    { name: "critical", total: 2 },
  ],
  recent_logs: [
    {
      id_log: 1,
      usuario: "report_admin",
      modulo: "inventario",
      accion: "inventory_audit",
      descripcion: "Auditoría",
      fecha: "2025-10-29T09:00:00Z",
      nivel: "warning",
      ip_origen: null,
    },
  ],
  recent_errors: [
    {
      id_error: 1,
      mensaje: "Fallo de sincronización",
      stack_trace: null,
      modulo: "sincronizacion",
      fecha: "2025-10-29T08:55:00Z",
      usuario: "report_admin",
    },
  ],
  alerts: [
    {
      type: "sync_failure",
      level: "critical",
      message: "1 eventos de sincronización fallidos para inventory",
      module: "inventory",
      occurred_at: "2025-10-29T08:45:00Z",
      reference: "inventory",
      count: 1,
    },
  ],
};

const dashboardSample: GlobalReportDashboard = {
  generated_at: "2025-10-29T10:30:00Z",
  filters: { date_from: null, date_to: null, module: null, severity: null },
  activity_series: [
    { date: "2025-10-28", info: 2, warning: 1, error: 0, critical: 1, system_errors: 0 },
    { date: "2025-10-29", info: 1, warning: 1, error: 1, critical: 1, system_errors: 1 },
  ],
  module_distribution: [
    { name: "inventario", total: 4 },
    { name: "sincronizacion", total: 4 },
  ],
  severity_distribution: [
    { name: "info", total: 3 },
    { name: "warning", total: 2 },
    { name: "error", total: 1 },
    { name: "critical", total: 2 },
  ],
};

describe("GlobalReportsDashboard", () => {
  beforeEach(() => {
    moduleStub.pushToast = vi.fn();
    (getGlobalReportOverview as unknown as Mock).mockResolvedValue(overviewSample);
    (getGlobalReportDashboard as unknown as Mock).mockResolvedValue(dashboardSample);
  });

  it("muestra métricas clave y alertas globales", async () => {
    render(<GlobalReportsDashboard />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /Registros totales/i })).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: /Errores críticos/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Sync pendientes/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Alertas automáticas/i })).toBeInTheDocument();
    expect(screen.getByText(/1 eventos de sincronización/i)).toBeInTheDocument();
  });
});
