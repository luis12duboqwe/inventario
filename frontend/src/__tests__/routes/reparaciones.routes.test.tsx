import React from "react";
import { describe, expect, it, beforeEach, beforeAll, vi } from "vitest";
import { MemoryRouter, Route, Routes, Outlet } from "react-router-dom";
import { act, render, screen, waitFor } from "@testing-library/react";

const repairsModuleResolvers = new Map<string, () => void>();
const repairsResolvers = new Map<string, () => void>();
let suspenseRunId = 0;
let ReparacionesLayout: React.ComponentType;

const createLazyStub = (label: string) => {
  let resolvedForRun = 0;
  let pending: Promise<void> | null = null;

  return function LazyStub() {
    if (resolvedForRun !== suspenseRunId) {
      if (!pending) {
        pending = new Promise<void>((resolve) => {
          repairsResolvers.set(label, () => {
            resolvedForRun = suspenseRunId;
            pending = null;
            resolve();
          });
        });
      }
      throw pending;
    }
    return <div>{label}</div>;
  };
};

vi.mock("framer-motion", () => {
  const NoopComponent = ({ children, ...rest }: { children?: React.ReactNode }) => (
    <div {...rest}>{children}</div>
  );

  return {
    __esModule: true,
    motion: new Proxy(
      {},
      {
        get: () => NoopComponent,
      },
    ),
    AnimatePresence: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
  };
});

vi.mock("../../modules/dashboard/layout/DashboardLayout", () => ({
  __esModule: true,
  default: () => (
    <div data-testid="dashboard-layout">
      <Outlet />
    </div>
  ),
}));

vi.mock("../../components/layout/PageHeader", () => ({
  __esModule: true,
  default: ({ title, subtitle }: { title: string; subtitle?: string }) => (
    <header>
      <h1>{title}</h1>
      {subtitle ? <p>{subtitle}</p> : null}
    </header>
  ),
}));

vi.mock("../../components/layout/PageToolbar", () => ({
  __esModule: true,
  default: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("@components/ui/Skeleton", () => ({
  Skeleton: () => <div data-testid="loading-skeleton">Cargando...</div>,
}));

const loaderMock = vi.fn(({ message }: { message?: string }) => (
  <div data-testid={`loader:${message ?? "Cargando"}`}>{message ?? "Cargando"}</div>
));

vi.mock("../../components/common/Loader", () => ({
  __esModule: true,
  default: loaderMock,
}));

vi.mock("../../modules/repairs/pages/RepairsPendingPage", () => ({
  __esModule: true,
  default: createLazyStub("Reparaciones: Pendientes"),
}));

vi.mock("../../modules/repairs/pages/RepairsInProgressPage", () => ({
  __esModule: true,
  default: createLazyStub("Reparaciones: En proceso"),
}));

vi.mock("../../modules/repairs/pages/RepairsReadyPage", () => ({
  __esModule: true,
  default: createLazyStub("Reparaciones: Listas"),
}));

vi.mock("../../modules/repairs/pages/RepairsDeliveredPage", () => ({
  __esModule: true,
  default: createLazyStub("Reparaciones: Entregadas"),
}));

vi.mock("../../modules/repairs/pages/RepairsPartsPage", () => ({
  __esModule: true,
  default: createLazyStub("Reparaciones: Repuestos"),
}));

vi.mock("../../modules/repairs/pages/RepairsBudgetsPage", () => ({
  __esModule: true,
  default: createLazyStub("Reparaciones: Presupuestos"),
}));

const mockRepairsModule = {
  token: "demo-token",
  stores: [],
  selectedStoreId: null,
  setSelectedStoreId: vi.fn(),
  refreshInventoryAfterTransfer: vi.fn(),
  enablePurchasesSales: true,
};

vi.mock("../../modules/repairs/hooks/useRepairsModule", () => ({
  __esModule: true,
  useRepairsModule: () => mockRepairsModule,
}));

vi.mock("../../modules/repairs/pages/RepairsPage", async () => {
  const actual = await vi.importActual<typeof import("../../modules/repairs/pages/RepairsPage")>(
    "../../modules/repairs/pages/RepairsPage",
  );

  let resolvedForRun = 0;
  let pending: Promise<void> | null = null;

  const SuspendedRepairsPage = () => {
    if (resolvedForRun !== suspenseRunId) {
      if (!pending) {
        // eslint-disable-next-line react-hooks/globals
        pending = new Promise<void>((resolve) => {
          repairsModuleResolvers.set("repairs", () => {
            resolvedForRun = suspenseRunId;
            pending = null;
            resolve();
          });
        });
      }
      throw pending;
    }
    return <actual.default />;
  };

  return {
    __esModule: true,
    default: SuspendedRepairsPage,
  };
});

beforeAll(async () => {
  const actual = await vi.importActual<
    typeof import("../../modules/repairs/pages/ReparacionesLayout")
  >("../../modules/repairs/pages/ReparacionesLayout");

  ReparacionesLayout = actual.default;
});

import DashboardRoutes from "../../modules/dashboard/routes";

const renderDashboardRoute = (initialPath: string) =>
  render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route
          path="/dashboard/*"
          element={<DashboardRoutes theme="dark" onToggleTheme={() => {}} onLogout={() => {}} />}
        />
      </Routes>
    </MemoryRouter>,
  );

const renderRepairsLayout = (initialPath: string) => {
  const PendingStub = createLazyStub("Reparaciones: Pendientes");
  const InProgressStub = createLazyStub("Reparaciones: En proceso");
  const ReadyStub = createLazyStub("Reparaciones: Listas");
  const DeliveredStub = createLazyStub("Reparaciones: Entregadas");
  const PartsStub = createLazyStub("Reparaciones: Repuestos");
  const BudgetsStub = createLazyStub("Reparaciones: Presupuestos");

  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/" element={<ReparacionesLayout />}>
          <Route path="pendientes" element={<PendingStub />} />
          <Route path="en-proceso" element={<InProgressStub />} />
          <Route path="listas" element={<ReadyStub />} />
          <Route path="entregadas" element={<DeliveredStub />} />
          <Route path="repuestos" element={<PartsStub />} />
          <Route path="presupuestos" element={<BudgetsStub />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
};

describe("Rutas de reparaciones", () => {
  beforeEach(() => {
    mockRepairsModule.enablePurchasesSales = true;
    suspenseRunId += 1;
    repairsModuleResolvers.clear();
    repairsResolvers.clear();
    loaderMock.mockClear();
  });

  it.each([
    ["pendientes", "Reparaciones: Pendientes"],
    ["en-proceso", "Reparaciones: En proceso"],
    ["listas", "Reparaciones: Listas"],
    ["entregadas", "Reparaciones: Entregadas"],
    ["repuestos", "Reparaciones: Repuestos"],
    ["presupuestos", "Reparaciones: Presupuestos"],
  ])("renderiza /dashboard/repairs/%s", async (segmento, textoEsperado) => {
    renderDashboardRoute(`/dashboard/repairs/${segmento}`);

    await waitFor(() => expect(repairsModuleResolvers.has("repairs")).toBe(true));
    await act(async () => {
      repairsModuleResolvers.get("repairs")?.();
    });

    await waitFor(() => expect(repairsResolvers.has(textoEsperado)).toBe(true));
    await act(async () => {
      repairsResolvers.get(textoEsperado)?.();
    });

    await expect(screen.findByText(textoEsperado)).resolves.toBeInTheDocument();
  });

  it("redirige /dashboard/repairs al índice de pendientes", async () => {
    renderDashboardRoute("/dashboard/repairs");

    await waitFor(() => expect(repairsModuleResolvers.has("repairs")).toBe(true));
    await act(async () => {
      repairsModuleResolvers.get("repairs")?.();
    });

    await waitFor(() => expect(repairsResolvers.has("Reparaciones: Pendientes")).toBe(true));
    await act(async () => {
      repairsResolvers.get("Reparaciones: Pendientes")?.();
    });

    await expect(screen.findByText("Reparaciones: Pendientes")).resolves.toBeInTheDocument();
  });

  it("muestra el loader del módulo mientras carga la ruta perezosa", async () => {
    renderDashboardRoute("/dashboard/repairs/pendientes");

    await waitFor(() => expect(repairsModuleResolvers.has("repairs")).toBe(true));
    expect(screen.getAllByTestId("loading-skeleton")[0]).toBeInTheDocument();

    await act(async () => {
      repairsModuleResolvers.get("repairs")?.();
    });

    await waitFor(() => expect(repairsResolvers.has("Reparaciones: Pendientes")).toBe(true));

    await act(async () => {
      repairsResolvers.get("Reparaciones: Pendientes")?.();
    });
    await expect(screen.findByText("Reparaciones: Pendientes")).resolves.toBeInTheDocument();
  });

  it("usa Suspense en el layout de reparaciones", async () => {
    renderRepairsLayout("/listas");

    await waitFor(() => expect(screen.getAllByTestId("loading-skeleton")[0]).toBeInTheDocument());

    await waitFor(() => expect(repairsResolvers.has("Reparaciones: Listas")).toBe(true));

    await act(async () => {
      repairsResolvers.get("Reparaciones: Listas")?.();
    });
    await expect(screen.findByText("Reparaciones: Listas")).resolves.toBeInTheDocument();
  });

  it("renderiza las pestañas de navegación del módulo", async () => {
    renderDashboardRoute("/dashboard/repairs/pendientes");

    await waitFor(() => expect(repairsModuleResolvers.has("repairs")).toBe(true));
    await act(async () => {
      repairsModuleResolvers.get("repairs")?.();
    });
    await expect(screen.findByRole("link", { name: "Pendientes" })).resolves.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "En proceso" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Listas" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Entregadas" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Repuestos" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Presupuestos" })).toBeInTheDocument();
  });
});
