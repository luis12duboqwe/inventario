import { render, screen, waitFor } from "@testing-library/react";
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

vi.mock("../../../catalog/components/PriceLists", () => ({
  __esModule: true,
  default: () => <div data-testid="catalog-price-lists" />,
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
import InventoryPriceListsPage from "../InventoryPriceListsPage";
import InventoryMovementsPage from "../InventoryMovementsPage";
import InventorySuppliersPage from "../InventorySuppliersPage";
import InventoryAlertsPage from "../InventoryAlertsPage";
import InventoryReservationsPage from "../InventoryReservationsPage";
import { useInventoryLayoutState } from "../useInventoryLayoutState";
import * as corporateReasonModule from "../../../../utils/corporateReason";
import type { InventoryReservation } from "../../../../api";

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
    updateStatus: null,
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
    storeValuationSnapshot: {
      storeId: 1,
      storeName: "Sucursal Centro",
      registeredValue: 1000,
      calculatedValue: 1000,
      difference: 0,
      differenceAbs: 0,
      differencePercent: 0,
      hasRelevantDifference: false,
    },
    fetchInventoryCurrentReport: vi.fn(),
    downloadInventoryCurrentCsv: vi.fn(),
    downloadInventoryCurrentPdf: vi.fn(),
    downloadInventoryCurrentXlsx: vi.fn(),
    fetchInventoryValueReport: vi.fn(),
    fetchInventoryMovementsReport: vi.fn(),
    fetchTopProductsReport: vi.fn(),
    fetchInactiveProductsReport: vi.fn(),
    fetchSyncDiscrepancyReport: vi.fn(),
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
    setSmartPreviewDirty: vi.fn(),
    smartFileInputRef: { current: null },
    handleSmartOverrideChange: vi.fn(),
    handleSmartPreview: vi.fn(),
    handleSmartCommit: vi.fn(),
    resetSmartImportContext: vi.fn(),
    vendorTemplates: [],
    applyVendorTemplate: vi.fn(),
    smartImportGuideUrl: "/docs/importacion/proveedores",
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
    storeValuationSnapshot: {
      storeId: 1,
      storeName: "Sucursal Centro",
      registeredValue: 1000,
      calculatedValue: 1000,
      difference: 0,
      differenceAbs: 0,
      differencePercent: 0,
      hasRelevantDifference: false,
    },
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
  reservations: {
    items: [],
    meta: { page: 1, size: 25, total: 0, pages: 0 },
    loading: false,
    includeExpired: false,
    setIncludeExpired: vi.fn(),
    refresh: vi.fn().mockResolvedValue(undefined),
    create: vi.fn().mockResolvedValue(undefined),
    renew: vi.fn().mockResolvedValue(undefined),
    cancel: vi.fn().mockResolvedValue(undefined),
    expiringSoon: [],
  },
  labeling: {
    open: false,
    device: null,
    storeId: null,
    storeName: null,
    openLabelPrinter: vi.fn(),
    closeLabelPrinter: vi.fn(),
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
        { id: "listas", label: "Listas de precios", icon: null },
        { id: "movimientos", label: "Movimientos", icon: null },
        { id: "reservas", label: "Reservas", icon: null },
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
    expect(screen.getByRole("tab", { name: /Listas de precios/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Movimientos/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Reservas/i })).toBeInTheDocument();
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

describe("InventoryPriceListsPage", () => {
  it("incluye el componente de listas de precios", () => {
    const contextValue = createContextValue();
    render(
      <InventoryLayoutContext.Provider value={contextValue}>
        <InventoryPriceListsPage />
      </InventoryLayoutContext.Provider>,
    );

    expect(screen.getByRole("heading", { name: /Listas de precios/i })).toBeInTheDocument();
    expect(screen.getByTestId("catalog-price-lists")).toBeInTheDocument();
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

describe("InventoryReservationsPage", () => {
  it("permite crear, renovar y cancelar reservas", async () => {
    const user = userEvent.setup();
    const contextValue = createContextValue();
    const device = {
      id: 10,
      sku: "SKU-RES-01",
      name: "Equipo reservado",
      quantity: 5,
    } as (typeof contextValue.module.devices)[number];
    contextValue.module.devices = [device];
    contextValue.module.selectedStoreId = 1;
    contextValue.module.selectedStore = { id: 1, name: "Sucursal Centro" } as never;

    const now = new Date();
    const reservation: InventoryReservation = {
      id: 99,
      store_id: 1,
      device_id: device.id,
      status: "RESERVADO",
      initial_quantity: 1,
      quantity: 1,
      reason: "Reserva inicial",
      resolution_reason: null,
      reference_type: null,
      reference_id: null,
      expires_at: new Date(now.getTime() + 30 * 60 * 1000).toISOString(),
      created_at: now.toISOString(),
      updated_at: now.toISOString(),
      reserved_by_id: 7,
      resolved_by_id: null,
      resolved_at: null,
      consumed_at: null,
      device,
    };

    const createMock = vi.fn().mockResolvedValue(undefined);
    const renewMock = vi.fn().mockResolvedValue(undefined);
    const cancelMock = vi.fn().mockResolvedValue(undefined);
    const refreshMock = vi.fn().mockResolvedValue(undefined);
    const setIncludeExpiredMock = vi.fn();
    contextValue.reservations = {
      items: [reservation],
      meta: { page: 1, size: 25, total: 1, pages: 1 },
      loading: false,
      includeExpired: false,
      setIncludeExpired: setIncludeExpiredMock,
      refresh: refreshMock,
      create: createMock,
      renew: renewMock,
      cancel: cancelMock,
      expiringSoon: [reservation],
    };

    const reasonSpy = vi
      .spyOn(corporateReasonModule, "promptCorporateReason")
      .mockReturnValue("Motivo válido");
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});
    const promptSpy = vi
      .spyOn(window, "prompt")
      .mockReturnValue("2031-01-01T10:15");

    render(
      <InventoryLayoutContext.Provider value={contextValue}>
        <InventoryReservationsPage />
      </InventoryLayoutContext.Provider>,
    );

    expect(
      screen.getByRole("heading", { name: /Reservas de inventario/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/reservas vencerán en los próximos 30 minutos/i),
    ).toBeInTheDocument();
    expect(screen.getByText("RESERVADO")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/Producto/i), `${device.id}`);
    const quantityInput = screen.getByLabelText(/Cantidad/i);
    await user.clear(quantityInput);
    await user.type(quantityInput, "2");
    const expirationInput = screen.getByLabelText(/Expira/i);
    await user.clear(expirationInput);
    await user.type(expirationInput, "2030-05-01T12:30");

    await user.click(screen.getByRole("button", { name: /Reservar unidades/i }));
    await waitFor(() => expect(createMock).toHaveBeenCalled());

    const [createInput, createReason] = createMock.mock.calls[0];
    expect(createInput.device_id).toBe(device.id);
    expect(createInput.quantity).toBe(2);
    expect(new Date(createInput.expires_at).getUTCFullYear()).toBe(2030);
    expect(createReason).toBe("Motivo válido");

    await user.click(screen.getByLabelText(/Mostrar vencidas/i));
    await waitFor(() => expect(setIncludeExpiredMock).toHaveBeenCalledWith(true));
    expect(refreshMock).toHaveBeenCalledWith(1);

    promptSpy.mockReturnValue("2032-02-02T08:45");
    await user.click(screen.getByRole("button", { name: /Renovar/i }));
    await waitFor(() => expect(renewMock).toHaveBeenCalled());

    const [renewId, renewPayload, renewReason] = renewMock.mock.calls[0];
    expect(renewId).toBe(reservation.id);
    expect(new Date(renewPayload.expires_at).getUTCFullYear()).toBe(2032);
    expect(renewReason).toBe("Motivo válido");

    await user.click(screen.getByRole("button", { name: /Cancelar/i }));
    await waitFor(() => expect(cancelMock).toHaveBeenCalledWith(reservation.id, "Motivo válido"));

    expect(reasonSpy).toHaveBeenCalled();
    expect(confirmSpy).toHaveBeenCalled();
    expect(alertSpy).not.toHaveBeenCalled();

    reasonSpy.mockRestore();
    confirmSpy.mockRestore();
    alertSpy.mockRestore();
    promptSpy.mockRestore();
  });
});
