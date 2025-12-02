import { render, screen, fireEvent } from "@testing-library/react";
import { describe, beforeEach, expect, it, vi } from "vitest";

import TechMonitor from "../TechMonitor";
import type { ObservabilitySnapshot } from "../../../../api";

const refreshMock = vi.fn();

type DashboardStub = {
  observability: ObservabilitySnapshot | null;
  observabilityError: string | null;
  observabilityLoading: boolean;
  refreshObservability: () => Promise<void> | void;
};

const snapshot: ObservabilitySnapshot = {
  generated_at: "2025-02-25T10:00:00.000Z",
  latency: {
    average_seconds: 45,
    percentile_95_seconds: 120,
    max_seconds: 240,
    samples: [
      {
        entity_type: "sale",
        pending: 2,
        failed: 3,
        oldest_pending_seconds: 180,
        latest_update: "2025-02-25T09:58:00.000Z",
      },
    ],
  },
  errors: {
    total_logs: 4,
    total_errors: 2,
    info: 1,
    warning: 1,
    error: 1,
    critical: 1,
    latest_error_at: "2025-02-25T09:40:00.000Z",
  },
  sync: {
    outbox_stats: [
      {
        entity_type: "sale",
        priority: "HIGH",
        total: 10,
        pending: 4,
        failed: 3,
        conflicts: 0,
        latest_update: "2025-02-25T09:58:00.000Z",
        oldest_pending: "2025-02-25T09:20:00.000Z",
      },
    ],
    total_pending: 4,
    total_failed: 3,
    hybrid_progress: {
      percent: 75,
      total: 20,
      processed: 15,
      pending: 5,
      failed: 3,
      components: {
        queue: {
          total: 10,
          processed: 7,
          pending: 2,
          failed: 1,
          latest_update: "2025-02-25T09:57:00.000Z",
          oldest_pending: "2025-02-25T09:20:00.000Z",
        },
        outbox: {
          total: 10,
          processed: 8,
          pending: 3,
          failed: 2,
          latest_update: "2025-02-25T09:58:00.000Z",
          oldest_pending: "2025-02-25T09:25:00.000Z",
        },
      },
    },
  },
  logs: [
    {
      id_log: 1,
      usuario: "admin",
      modulo: "sync",
      accion: "sync_failure",
      descripcion: "Se detectó un error en la cola",
      fecha: "2025-02-25T09:50:00.000Z",
      nivel: "error",
      ip_origen: null,
    },
  ],
  system_errors: [
    {
      id_error: 1,
      mensaje: "Timeout de sincronización",
      stack_trace: null,
      modulo: "sync",
      fecha: "2025-02-25T09:45:00.000Z",
      usuario: "admin",
    },
  ],
  alerts: [],
  notifications: [
    {
      id: "sync-outbox-sale",
      title: "Fallas en sincronización",
      message: "3 eventos fallidos en la entidad sale.",
      severity: "error",
      occurred_at: "2025-02-25T09:58:00.000Z",
      reference: "sale",
    },
  ],
};

const dashboardState: DashboardStub = {
  observability: snapshot,
  observabilityError: null,
  observabilityLoading: false,
  refreshObservability: refreshMock,
};

vi.mock("../../context/DashboardContext", () => ({
  useDashboard: () => dashboardState,
}));

describe("TechMonitor", () => {
  beforeEach(() => {
    dashboardState.observability = snapshot;
    dashboardState.observabilityError = null;
    dashboardState.observabilityLoading = false;
    refreshMock.mockReset();
  });

  it("muestra métricas, alertas y registros recientes", () => {
    render(<TechMonitor />);

    expect(screen.getByRole("heading", { name: "Monitor tecnológico" })).toBeInTheDocument();
    expect(screen.getByText(/Latencia promedio/i)).toBeInTheDocument();
    expect(screen.getByText("45 s")).toBeInTheDocument();
    expect(screen.getByText(/Fallas en sincronización/i)).toBeInTheDocument();
    expect(screen.getByText(/3 eventos fallidos en la entidad sale./i)).toBeInTheDocument();
    expect(screen.getByText(/Se detectó un error en la cola/i)).toBeInTheDocument();
  });

  it("permite actualizar manualmente las métricas", () => {
    render(<TechMonitor />);

    const button = screen.getByRole("button", { name: /Actualizar/i });
    fireEvent.click(button);
    expect(refreshMock).toHaveBeenCalledTimes(1);
  });

  it("muestra estado de carga cuando no hay snapshot disponible", () => {
    dashboardState.observability = null;
    dashboardState.observabilityLoading = true;

    render(<TechMonitor />);

    expect(screen.getByRole("status", { hidden: true })).toBeInTheDocument();
  });

  it("muestra mensaje de error cuando la API de observabilidad falla", () => {
    dashboardState.observabilityError = "No hay conexión con el monitor corporativo";

    render(<TechMonitor />);

    expect(screen.getByText(/No hay conexión con el monitor corporativo/i)).toBeInTheDocument();
  });
});
