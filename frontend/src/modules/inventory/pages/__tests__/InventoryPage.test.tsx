import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../useInventoryLayoutState", () => ({
  useInventoryLayoutState: vi.fn(),
}));

vi.mock("../components/DeviceEditDialog", () => ({
  __esModule: true,
  default: ({ open }: { open: boolean }) =>
    open ? <div data-testid="inventory-edit-dialog" /> : null,
}));
vi.mock("../components/DeviceEditDialog.tsx", () => ({
  __esModule: true,
  default: ({ open }: { open: boolean }) =>
    open ? <div data-testid="inventory-edit-dialog" /> : null,
}));
vi.mock("/src/modules/inventory/components/DeviceEditDialog", () => ({
  __esModule: true,
  default: ({ open }: { open: boolean }) =>
    open ? <div data-testid="inventory-edit-dialog" /> : null,
}));
vi.mock("/src/modules/inventory/components/DeviceEditDialog.tsx", () => ({
  __esModule: true,
  default: ({ open }: { open: boolean }) =>
    open ? <div data-testid="inventory-edit-dialog" /> : null,
}));

vi.mock("../components/InventoryStatusSection", () => ({
  __esModule: true,
  default: () => <div data-testid="inventory-status-section" />,
}));

vi.mock("../components/InventoryProductsTableSection", () => ({
  __esModule: true,
  default: () => <div data-testid="inventory-products-table" />,
}));

vi.mock("../components/InventoryCatalogToolsSection", () => ({
  __esModule: true,
  default: () => <div data-testid="inventory-catalog-tools" />,
}));

vi.mock("../components/InventorySmartImportSection", () => ({
  __esModule: true,
  default: () => <div data-testid="inventory-smart-import" />,
}));

vi.mock("../components/InventoryCorrectionsSection", () => ({
  __esModule: true,
  default: () => <div data-testid="inventory-corrections" />,
}));

vi.mock("../components/InventoryProductsFilters", () => ({
  __esModule: true,
  default: () => <div data-testid="inventory-products-filters" />,
}));

vi.mock("../components/InventoryMovementFormSection", () => ({
  __esModule: true,
  default: () => <div data-testid="inventory-movement-form" />,
}));

vi.mock("../components/InventoryTransferFormSection", () => ({
  __esModule: true,
  default: () => <div data-testid="inventory-transfer-form" />, // [PACK30-31-FRONTEND]
}));

vi.mock("../components/InventoryMovementsTimelineSection", () => ({
  __esModule: true,
  default: () => <div data-testid="inventory-movements-timeline" />,
}));

vi.mock("../components/InventorySuppliersSection", () => ({
  __esModule: true,
  default: () => <div data-testid="inventory-suppliers-section" />,
}));

vi.mock("../components/InventoryAlertsSection", () => ({
  __esModule: true,
  default: () => <div data-testid="inventory-alerts-section" />,
}));

import InventoryLayoutContext, {
  type InventoryLayoutContextValue,
} from "../context/InventoryLayoutContext";
import InventoryPage from "../InventoryPage";
import InventoryProductsPage from "../InventoryProductsPage";
import InventoryMovementsPage from "../InventoryMovementsPage";
import InventorySuppliersPage from "../InventorySuppliersPage";
import InventoryAlertsPage from "../InventoryAlertsPage";
import { useInventoryLayoutState } from "../useInventoryLayoutState";

const useInventoryLayoutStateMock = vi.mocked(useInventoryLayoutState);

type Mutable<T> = { -readonly [P in keyof T]: T[P] };

const createContextValue = (): InventoryLayoutContextValue => ({
  module: {
    token: "token",
    enableCatalogPro: true,
    stores: [],
    selectedStoreId: 1,
    setSelectedStoreId: vi.fn(),
    selectedStore: { id: 1, name: "Sucursal Centro" } as unknown as InventoryLayoutContextValue["module"]["selectedStore"],
    devices: [],
    loading: false,
    totalDevices: 0,
    totalItems: 0,
    totalValue: 0,
    formatCurrency: vi.fn().mockImplementation((value: number) => `$${value}`),
    topStores: [],
    lowStockDevices: [],
    handleMovement: vi.fn(),
    handleDeviceUpdate: vi.fn(),
    backupHistory: [],
    updateStatus: vi.fn(),
    lastInventoryRefresh: new Date("2025-01-01T00:00:00Z"),
    downloadInventoryReport: vi.fn(),
    downloadInventoryCsv: vi.fn(),
    exportCatalogCsv: vi.fn(),
    importCatalogCsv: vi.fn(),
    supplierBatchOverview: [],
    supplierBatchLoading: false,
    refreshSupplierBatchOverview: vi.fn(),
    stockByCategory: [],
    recentMovements: [],
    recentMovementsLoading: false,
    refreshRecentMovements: vi.fn(),
    lowStockThreshold: 5,
    updateLowStockThreshold: vi.fn(),
    refreshSummary: vi.fn(),
    storeValuationSnapshot: [],
    fetchInventoryCurrentReport: vi.fn(),
    downloadInventoryCurrentCsv: vi.fn(),
    downloadInventoryCurrentPdf: vi.fn(),
    downloadInventoryCurrentXlsx: vi.fn(),
    fetchInventoryValueReport: vi.fn(),
    fetchInventoryMovementsReport: vi.fn(),
    fetchTopProductsReport: vi.fn(),
    downloadInventoryValueCsv: vi.fn(),
    downloadInventoryValuePdf: vi.fn(),
    downloadInventoryValueXlsx: vi.fn(),
    downloadInventoryMovementsCsv: vi.fn(),
    downloadInventoryMovementsPdf: vi.fn(),
    downloadInventoryMovementsXlsx: vi.fn(),
    downloadTopProductsCsv: vi.fn(),
    downloadTopProductsPdf: vi.fn(),
    downloadTopProductsXlsx: vi.fn(),
    smartImportInventory: vi.fn(),
    fetchSmartImportHistory: vi.fn(),
    fetchIncompleteDevices: vi.fn(),
  },
  smartImport: {
    smartImportFile: null,
    setSmartImportFile: vi.fn(),
    smartImportPreviewState: { status: "idle" } as unknown as Mutable<InventoryLayoutContextValue["smartImport"]["smartImportPreviewState"]>,
    smartImportResult: null,
    smartImportOverrides: {},
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
    highlightedDeviceIds: new Set(),
  },
  editing: {
    editingDevice: null,
    openEditDialog: vi.fn(),
    closeEditDialog: vi.fn(),
    isEditDialogOpen: false,
    handleSubmitDeviceUpdates: vi.fn().mockResolvedValue(undefined),
  },
  metrics: {
    statusCards: [],
    storeValuationSnapshot: [],
    lastBackup: null,
    lastRefreshDisplay: "Hace un momento",
    totalCategoryUnits: 0,
    categoryChartData: [],
    moduleStatus: "ok",
    moduleStatusLabel: "Inventario saludable",
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
    thresholdDraft: 5,
    setThresholdDraft: vi.fn(),
    updateThresholdDraftValue: vi.fn(),
    handleSaveThreshold: vi.fn().mockResolvedValue(undefined),
    isSavingThreshold: false,
  },
  helpers: {
    storeNameById: new Map(),
    resolvePendingFields: vi.fn().mockReturnValue([]),
    resolveLowStockSeverity: vi.fn().mockReturnValue("notice"),
  },
});

describe("InventoryPage", () => {
  const handleTabChange = vi.fn();
  const closeEditDialog = vi.fn();
  const handleSubmitDeviceUpdates = vi.fn().mockResolvedValue(undefined);

  beforeEach(() => {
    handleTabChange.mockReset();
    closeEditDialog.mockReset();
    handleSubmitDeviceUpdates.mockReset();
    useInventoryLayoutStateMock.mockReturnValue({
      contextValue: createContextValue(),
      tabOptions: [
        { id: "productos", label: "Productos", icon: null },
        { id: "movimientos", label: "Movimientos", icon: null },
      ],
      activeTab: "productos",
      handleTabChange,
      moduleStatus: "ok",
      moduleStatusLabel: "Inventario saludable",
      loading: false,
      editingDevice: null,
      isEditDialogOpen: false,
      closeEditDialog,
      handleSubmitDeviceUpdates,
    });
  });

  it("renderiza encabezado y pestañas", () => {
    render(
      <MemoryRouter>
        <InventoryPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: /Inventario corporativo/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Productos/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Movimientos/i })).toBeInTheDocument();
  });

  it("cambia de pestaña al hacer clic", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <InventoryPage />
      </MemoryRouter>,
    );

    const movimientosTab = screen.getByRole("tab", { name: /Movimientos/i });
    await user.click(movimientosTab);

    expect(handleTabChange).toHaveBeenCalledWith("movimientos");
  });

  it("muestra indicador de carga y diálogo de edición", async () => {
    useInventoryLayoutStateMock.mockReturnValue({
      contextValue: createContextValue(),
      tabOptions: [{ id: "productos", label: "Productos", icon: null }],
      activeTab: "productos",
      handleTabChange,
      moduleStatus: "warning",
      moduleStatusLabel: "Sincronizando",
      loading: true,
      editingDevice: { id: 1 } as never,
      isEditDialogOpen: true,
      closeEditDialog,
      handleSubmitDeviceUpdates,
    });

    render(
      <MemoryRouter>
        <InventoryPage />
      </MemoryRouter>,
    );

    expect(screen.getByText(/Sincronizando inventario/i)).toBeInTheDocument();
    expect(await screen.findByTestId("inventory-edit-dialog")).toBeInTheDocument();
  });
});

describe("InventoryProductsPage", () => {
  it("ejecuta acciones de descarga y refresco", async () => {
    const user = userEvent.setup();
    const contextValue = createContextValue();
    render(
      <InventoryLayoutContext.Provider value={contextValue}>
        <InventoryProductsPage />
      </InventoryLayoutContext.Provider>,
    );

    await user.click(screen.getByRole("button", { name: /Descargar PDF/i }));
    await user.click(screen.getByRole("button", { name: /Descargar CSV/i }));
    await user.click(screen.getByRole("button", { name: /Actualizar métricas/i }));

    expect(contextValue.downloads.triggerDownloadReport).toHaveBeenCalled();
    expect(contextValue.downloads.triggerDownloadCsv).toHaveBeenCalled();
    expect(contextValue.downloads.triggerRefreshSummary).toHaveBeenCalled();

    expect(screen.getByTestId("inventory-status-section")).toBeInTheDocument();
    expect(screen.getByTestId("inventory-products-table")).toBeInTheDocument();
    expect(screen.getByTestId("inventory-catalog-tools")).toBeInTheDocument();
    expect(screen.getByTestId("inventory-smart-import")).toBeInTheDocument();
    expect(screen.getByTestId("inventory-corrections")).toBeInTheDocument();
  });
});

describe("InventoryMovementsPage", () => {
  it("muestra formulario y línea de tiempo", () => {
    render(
      <InventoryLayoutContext.Provider value={createContextValue()}>
        <InventoryMovementsPage />
      </InventoryLayoutContext.Provider>,
    );

    expect(screen.getByRole("heading", { name: /Movimientos de inventario/i })).toBeInTheDocument();
    expect(screen.getByTestId("inventory-movement-form")).toBeInTheDocument();
    expect(screen.getByTestId("inventory-movements-timeline")).toBeInTheDocument();
  });
});

describe("InventorySuppliersPage", () => {
  it("personaliza el subtítulo con la sucursal seleccionada", () => {
    const contextValue = createContextValue();
    contextValue.module.selectedStore = { id: 7, name: "Sucursal Norte" } as never;

    render(
      <InventoryLayoutContext.Provider value={contextValue}>
        <InventorySuppliersPage />
      </InventoryLayoutContext.Provider>,
    );

    expect(
      screen.getByText(/Compras recientes para Sucursal Norte/i),
    ).toBeInTheDocument();
    expect(screen.getByTestId("inventory-suppliers-section")).toBeInTheDocument();
  });
});

describe("InventoryAlertsPage", () => {
  it("adapta el subtítulo según la tienda", () => {
    const contextValue = createContextValue();
    contextValue.module.selectedStore = null;

    render(
      <InventoryLayoutContext.Provider value={contextValue}>
        <InventoryAlertsPage />
      </InventoryLayoutContext.Provider>,
    );

    expect(
      screen.getByText(/Selecciona una sucursal para ajustar el umbral de alertas/i),
    ).toBeInTheDocument();
    expect(screen.getByTestId("inventory-alerts-section")).toBeInTheDocument();
  });
});
