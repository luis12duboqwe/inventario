import React from "react";
import { describe, expect, it, beforeEach, vi } from "vitest";
import { MemoryRouter, Route, Routes, Outlet } from "react-router-dom";
import { act, render, screen, waitFor } from "@testing-library/react";

let resolveInventoryModule: (() => void) | null = null;
const resolveInventoryChild: Record<string, () => void> = {};
let suspenseRunId = 0;

const createLazyStub = (label: string) => {
  let resolvedForRun = 0;
  let pending: Promise<void> | null = null;

  return function LazyStub() {
    if (resolvedForRun !== suspenseRunId) {
      if (!pending) {
        pending = new Promise<void>((resolve) => {
          resolveInventoryChild[label] = () => {
            resolvedForRun = suspenseRunId;
            pending = null;
            resolve();
          };
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

vi.mock("../../modules/inventory/pages/components/DeviceEditDialog", () => ({
  __esModule: true,
  default: () => null,
}));

vi.mock("../../components/common/Loader", () => ({
  __esModule: true,
  default: ({ message }: { message?: string }) => <div>{message ?? "Cargando"}</div>,
}));

vi.mock("../../modules/inventory/pages/InventoryProductsPage", () => ({
  __esModule: true,
  default: createLazyStub("Inventario: Productos"),
}));

vi.mock("../../modules/inventory/pages/InventoryMovementsPage", () => ({
  __esModule: true,
  default: createLazyStub("Inventario: Movimientos"),
}));

vi.mock("../../modules/inventory/pages/InventorySuppliersPage", () => ({
  __esModule: true,
  default: createLazyStub("Inventario: Proveedores"),
}));

vi.mock("../../modules/inventory/pages/InventoryAlertsPage", () => ({
  __esModule: true,
  default: createLazyStub("Inventario: Alertas"),
}));

const mockInventoryState = {
  contextValue: {
    module: {},
    smartImport: {
      smartImportFile: null,
      setSmartImportFile: vi.fn(),
      smartImportPreviewState: null,
      smartImportResult: null,
      smartImportOverrides: new Map(),
      smartImportHeaders: [],
      smartImportLoading: false,
      smartImportHistory: [],
      smartImportHistoryLoading: false,
      refreshSmartImportHistory: vi.fn(),
      pendingDevices: [],
      pendingDevicesLoading: false,
      refreshPendingDevices: vi.fn(),
      smartPreviewDirty: false,
      smartFileInputRef: { current: null },
      handleSmartOverrideChange: vi.fn(),
      handleSmartPreview: vi.fn(),
      handleSmartCommit: vi.fn(),
      resetSmartImportContext: vi.fn(),
    },
    search: {
      inventoryQuery: "",
      setInventoryQuery: vi.fn(),
      estadoFilter: "TODOS",
      setEstadoFilter: vi.fn(),
      filteredDevices: [],
      highlightedDeviceIds: new Set<number>(),
    },
    editing: {
      editingDevice: null,
      openEditDialog: vi.fn(),
      closeEditDialog: vi.fn(),
      isEditDialogOpen: false,
      handleSubmitDeviceUpdates: vi.fn(),
    },
    metrics: {
      statusCards: [],
      storeValuationSnapshot: [],
      lastBackup: null,
      lastRefreshDisplay: "Hace un momento",
      totalCategoryUnits: 0,
      categoryChartData: [],
      moduleStatus: "ok",
      moduleStatusLabel: "Sincronizado",
      lowStockStats: { critical: 0, warning: 0 },
    },
    downloads: {
      triggerRefreshSummary: vi.fn(),
      triggerDownloadReport: vi.fn(),
      triggerDownloadCsv: vi.fn(),
      triggerExportCatalog: vi.fn(),
      triggerImportCatalog: vi.fn(),
      downloadSmartResultCsv: vi.fn(),
      downloadSmartResultPdf: vi.fn(),
      triggerRefreshSupplierOverview: vi.fn(),
      triggerRefreshRecentMovements: vi.fn(),
    },
    catalog: {
      catalogFile: null,
      setCatalogFile: vi.fn(),
      importingCatalog: false,
      exportingCatalog: false,
      lastImportSummary: null,
      fileInputRef: { current: null },
    },
    alerts: {
      thresholdDraft: 10,
      setThresholdDraft: vi.fn(),
      updateThresholdDraftValue: vi.fn(),
      handleSaveThreshold: vi.fn(),
      isSavingThreshold: false,
    },
    helpers: {
      storeNameById: new Map<number, string>(),
      resolvePendingFields: () => [],
      resolveLowStockSeverity: () => "warning" as const,
    },
  },
  tabOptions: [
    { id: "productos", label: "Productos", icon: <span aria-hidden="true" /> },
    { id: "movimientos", label: "Movimientos", icon: <span aria-hidden="true" /> },
    { id: "proveedores", label: "Proveedores", icon: <span aria-hidden="true" /> },
    { id: "alertas", label: "Alertas", icon: <span aria-hidden="true" /> },
  ],
  activeTab: "productos",
  handleTabChange: vi.fn(),
  moduleStatus: "ok",
  moduleStatusLabel: "Sincronizado",
  loading: false,
  editingDevice: null,
  isEditDialogOpen: false,
  closeEditDialog: vi.fn(),
  handleSubmitDeviceUpdates: vi.fn(),
};

vi.mock("../../modules/inventory/pages/useInventoryLayoutState", () => ({
  __esModule: true,
  useInventoryLayoutState: () => mockInventoryState,
}));

vi.mock("../../modules/inventory/pages/InventoryPage", async () => {
  const actual = await vi.importActual<
    typeof import("../../modules/inventory/pages/InventoryPage")
  >("../../modules/inventory/pages/InventoryPage");

  let resolvedForRun = 0;
  let pending: Promise<void> | null = null;

  const SuspendedInventoryPage = () => {
    if (resolvedForRun !== suspenseRunId) {
      if (!pending) {
        // eslint-disable-next-line react-hooks/globals
        pending = new Promise<void>((resolve) => {
          // eslint-disable-next-line react-hooks/globals
          resolveInventoryModule = () => {
            resolvedForRun = suspenseRunId;
            pending = null;
            resolve();
          };
        });
      }
      throw pending;
    }
    return <actual.default />;
  };

  return {
    __esModule: true,
    default: SuspendedInventoryPage,
  };
});

import DashboardRoutes from "../../modules/dashboard/routes";

const renderDashboardRoute = (initialPath: string) =>
  render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route
          path="/dashboard/*"
          element={
            <DashboardRoutes theme="dark" onToggleTheme={() => {}} onLogout={() => {}} />
          }
        />
      </Routes>
    </MemoryRouter>,
  );

const resolveInventoryRoute = async (label: string) => {
  await waitFor(() => expect(resolveInventoryModule).not.toBeNull());
  await act(async () => {
    resolveInventoryModule?.();
  });

  await waitFor(() => expect(resolveInventoryChild[label]).toBeDefined());
  await act(async () => {
    resolveInventoryChild[label]?.();
  });
};

describe("Rutas de inventario", () => {
  beforeEach(() => {
    mockInventoryState.activeTab = "productos";
    suspenseRunId += 1;
    resolveInventoryModule = null;
    Object.keys(resolveInventoryChild).forEach((key) => {
      delete resolveInventoryChild[key];
    });
  });

  it.each([
    ["productos", "Inventario: Productos"],
    ["movimientos", "Inventario: Movimientos"],
    ["proveedores", "Inventario: Proveedores"],
    ["alertas", "Inventario: Alertas"],
  ])("renderiza /dashboard/inventory/%s", async (segmento, textoEsperado) => {
    renderDashboardRoute(`/dashboard/inventory/${segmento}`);

    await resolveInventoryRoute(textoEsperado);
    await expect(screen.findByText(textoEsperado)).resolves.toBeInTheDocument();
  });

  it("redirige /dashboard/inventory al índice de productos", async () => {
    renderDashboardRoute("/dashboard/inventory");

    await resolveInventoryRoute("Inventario: Productos");
    await expect(screen.findByText("Inventario: Productos")).resolves.toBeInTheDocument();
  });

  it("muestra el loader de módulo mientras carga la ruta perezosa", async () => {
    renderDashboardRoute("/dashboard/inventory/productos");

    await waitFor(() => expect(resolveInventoryModule).not.toBeNull());
    expect(screen.getByText("Cargando panel…")).toBeInTheDocument();

    await act(async () => {
      resolveInventoryModule?.();
    });

    await waitFor(() => expect(resolveInventoryChild["Inventario: Productos"]).toBeDefined());
    await expect(
      screen.findByText("Cargando vista de inventario…"),
    ).resolves.toBeInTheDocument();

    await act(async () => {
      resolveInventoryChild["Inventario: Productos"]?.();
    });
    await expect(screen.findByText("Inventario: Productos")).resolves.toBeInTheDocument();
  });

  it("envuelve las subrutas en Suspense y muestra el loader interno", async () => {
    renderDashboardRoute("/dashboard/inventory/movimientos");

    await waitFor(() => expect(resolveInventoryModule).not.toBeNull());
    expect(screen.getByText("Cargando panel…")).toBeInTheDocument();

    await act(async () => {
      resolveInventoryModule?.();
    });

    await waitFor(() => expect(resolveInventoryChild["Inventario: Movimientos"]).toBeDefined());
    await expect(
      screen.findByText("Cargando vista de inventario…"),
    ).resolves.toBeInTheDocument();

    await act(async () => {
      resolveInventoryChild["Inventario: Movimientos"]?.();
    });
    await expect(screen.findByText("Inventario: Movimientos")).resolves.toBeInTheDocument();
  });
});
