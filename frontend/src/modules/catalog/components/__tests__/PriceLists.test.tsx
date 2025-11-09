import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../../dashboard/context/DashboardContext", () => ({
  useDashboard: vi.fn(),
}));

vi.mock("../../../inventory/pages/context/InventoryLayoutContext", () => ({
  useInventoryLayout: vi.fn(),
}));

vi.mock("../../../../api", () => ({
  listCustomers: vi.fn(),
}));

vi.mock("../../services/priceListsService", () => {
  const service = {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
    addItem: vi.fn(),
    updateItem: vi.fn(),
    removeItem: vi.fn(),
    getItem: vi.fn(),
    resolve: vi.fn(),
  };
  return { priceListsService: service };
});

vi.mock("../../../../utils/corporateReason", () => ({
  promptCorporateReason: vi.fn(),
}));

import PriceLists from "../PriceLists";
import { priceListsService } from "../../services/priceListsService";
import { listCustomers } from "../../../../api";
import { promptCorporateReason } from "../../../../utils/corporateReason";
import { useDashboard } from "../../../dashboard/context/DashboardContext";
import { useInventoryLayout } from "../../../inventory/pages/context/InventoryLayoutContext";

const listSpy = priceListsService.list as vi.Mock;
const createSpy = priceListsService.create as vi.Mock;
const updateSpy = priceListsService.update as vi.Mock;
const resolveSpy = priceListsService.resolve as vi.Mock;

const baseDashboard = {
  token: "token",
  enableCatalogPro: true,
  enableTransfers: true,
  enablePurchasesSales: true,
  enableAnalyticsAdv: true,
  enableTwoFactor: false,
  enableHybridPrep: true,
  compactMode: false,
  setCompactMode: vi.fn(),
  toggleCompactMode: vi.fn(),
  globalSearchTerm: "",
  setGlobalSearchTerm: vi.fn(),
  stores: [],
  summary: [],
  metrics: null,
  devices: [],
  backupHistory: [],
  releaseHistory: [],
  updateStatus: null,
  selectedStoreId: 1,
  setSelectedStoreId: vi.fn(),
  selectedStore: { id: 1, name: "Sucursal Centro" },
  loading: false,
  message: null,
  setMessage: vi.fn(),
  error: null,
  setError: vi.fn(),
  syncStatus: null,
  outbox: [],
  outboxError: null,
  outboxStats: [],
  syncQueueSummary: null,
  syncHybridProgress: null,
  syncHybridForecast: null,
  syncHybridBreakdown: [],
  syncHybridOverview: null,
  currentUser: null,
  syncHistory: [],
  syncHistoryError: null,
  formatCurrency: (value: number) => `$${value}`,
  totalDevices: 0,
  totalItems: 0,
  totalValue: 0,
  lowStockDevices: [],
  topStores: [],
  currentLowStockThreshold: 5,
  updateLowStockThreshold: vi.fn(),
  handleMovement: vi.fn(),
  handleDeviceUpdate: vi.fn(),
  refreshInventoryAfterTransfer: vi.fn(),
  refreshSummary: vi.fn(),
  lastInventoryRefresh: null,
  handleSync: vi.fn(),
  handleBackup: vi.fn(),
  refreshOutbox: vi.fn(),
  handleRetryOutbox: vi.fn(),
  downloadInventoryReport: vi.fn(),
  refreshOutboxStats: vi.fn(),
  refreshSyncQueueSummary: vi.fn(),
  refreshSyncHistory: vi.fn(),
  toasts: [],
  pushToast: vi.fn(),
  dismissToast: vi.fn(),
  networkAlert: null,
  dismissNetworkAlert: vi.fn(),
  refreshStores: vi.fn(),
};

const baseInventoryContext = {
  module: {
    token: "token",
    enableCatalogPro: true,
    stores: [{ id: 1, name: "Sucursal Centro" }],
    selectedStoreId: 1,
    setSelectedStoreId: vi.fn(),
    selectedStore: { id: 1, name: "Sucursal Centro" },
    devices: [
      {
        id: 101,
        name: "iPhone 15",
        sku: "IPH15",
        unit_price: 24999,
        precio_venta: 24999,
      },
    ],
    loading: false,
    totalDevices: 0,
    totalItems: 0,
    totalValue: 0,
    formatCurrency: (value: number) => `$${value}`,
    topStores: [],
    lowStockDevices: [],
    handleMovement: vi.fn(),
    handleDeviceUpdate: vi.fn(),
    backupHistory: [],
    updateStatus: null,
    lastInventoryRefresh: null,
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
    storeValuationSnapshot: null,
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
    reservations: [],
    reservationsMeta: { page: 1, size: 25, total: 0, pages: 0 },
    reservationsLoading: false,
    reservationsIncludeExpired: false,
    setReservationsIncludeExpired: vi.fn(),
    refreshReservations: vi.fn(),
    createReservation: vi.fn(),
    renewReservation: vi.fn(),
    cancelReservation: vi.fn(),
    expiringReservations: [],
  },
  smartImport: {
    smartImportFile: null,
    setSmartImportFile: vi.fn(),
    smartImportPreviewState: { status: "idle" },
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
    handleSubmitDeviceUpdates: vi.fn(),
  },
  metrics: {
    statusCards: [],
    storeValuationSnapshot: null,
    lastBackup: null,
    lastRefreshDisplay: "",
    totalCategoryUnits: 0,
    categoryChartData: [],
    moduleStatus: "ok",
    moduleStatusLabel: "",
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
    handleSaveThreshold: vi.fn(),
    isSavingThreshold: false,
  },
  helpers: {
    storeNameById: new Map(),
    resolvePendingFields: vi.fn(),
    resolveLowStockSeverity: vi.fn(),
  },
  reservations: {
    items: [],
    meta: { page: 1, size: 25, total: 0, pages: 0 },
    loading: false,
    includeExpired: false,
    setIncludeExpired: vi.fn(),
    refresh: vi.fn(),
    create: vi.fn(),
    renew: vi.fn(),
    cancel: vi.fn(),
    expiringSoon: [],
  },
};

describe("PriceLists", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listSpy.mockResolvedValue([]);
    createSpy.mockResolvedValue({
      id: 10,
      name: "Corporativo",
      description: null,
      is_active: true,
      store_id: 1,
      customer_id: null,
      currency: "MXN",
      valid_from: null,
      valid_until: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      items: [],
    });
    updateSpy.mockResolvedValue({
      id: 10,
      name: "Corporativo",
      description: null,
      is_active: true,
      store_id: 1,
      customer_id: null,
      currency: "MXN",
      valid_from: null,
      valid_until: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      items: [],
    });
    resolveSpy.mockResolvedValue(null);
    (listCustomers as unknown as vi.Mock).mockResolvedValue([]);
    (promptCorporateReason as unknown as vi.Mock).mockReturnValue("Motivo válido");
    (useDashboard as unknown as vi.Mock).mockReturnValue(baseDashboard);
    (useInventoryLayout as unknown as vi.Mock).mockReturnValue(baseInventoryContext);
    vi.spyOn(window, "prompt").mockReturnValue("Motivo válido");
  });

  it("muestra las listas de precios obtenidas del servicio", async () => {
    listSpy.mockResolvedValueOnce([
      {
        id: 1,
        name: "Mayoristas",
        description: "Lista regional",
        is_active: true,
        store_id: 1,
        customer_id: null,
        currency: "MXN",
        valid_from: "2025-01-01",
        valid_until: null,
        created_at: "2025-01-01T00:00:00Z",
        updated_at: "2025-01-01T00:00:00Z",
        items: [],
      },
      {
        id: 2,
        name: "Clientes VIP",
        description: null,
        is_active: false,
        store_id: null,
        customer_id: 99,
        currency: "MXN",
        valid_from: null,
        valid_until: null,
        created_at: "2025-01-02T00:00:00Z",
        updated_at: "2025-01-02T00:00:00Z",
        items: [],
      },
    ]);

    render(<PriceLists />);

    const aside = await screen.findByRole("complementary");
    const list = within(aside);

    expect(list.getByText("Mayoristas")).toBeInTheDocument();
    expect(list.getByText("Clientes VIP")).toBeInTheDocument();
  });

  it("impide guardar cuando el motivo corporativo es inválido", async () => {
    listSpy.mockResolvedValueOnce([]);
    (promptCorporateReason as unknown as vi.Mock).mockReturnValueOnce("abc");

    render(<PriceLists />);

    await waitFor(() => expect(listSpy).toHaveBeenCalledTimes(1));

    const user = userEvent.setup();
    const nameInput = await screen.findByLabelText(/Nombre/i);
    await user.clear(nameInput);
    await user.type(nameInput, "Lista test");

    await user.click(screen.getByRole("button", { name: /Guardar cambios/i }));

    await waitFor(() => {
      expect(createSpy).not.toHaveBeenCalled();
      expect(baseDashboard.pushToast).toHaveBeenCalledWith(
        expect.objectContaining({
          variant: "error",
          message: expect.stringContaining("motivo corporativo"),
        }),
      );
    });
  });

  it("crea una lista de precios cuando el motivo es válido", async () => {
    listSpy.mockResolvedValueOnce([]);
    listSpy.mockResolvedValueOnce([
      {
        id: 10,
        name: "Corporativo",
        description: null,
        is_active: true,
        store_id: 1,
        customer_id: null,
        currency: "MXN",
        valid_from: null,
        valid_until: null,
        created_at: "2025-01-03T00:00:00Z",
        updated_at: "2025-01-03T00:00:00Z",
        items: [],
      },
    ]);

    render(<PriceLists />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /Nueva lista/i }));
    const nameInput = await screen.findByLabelText(/Nombre/i);
    await user.clear(nameInput);
    await user.type(nameInput, "Lista corporativa");

    await user.click(screen.getByRole("button", { name: /Guardar cambios/i }));

    await waitFor(() => expect(promptCorporateReason).toHaveBeenCalled());

    expect(updateSpy).not.toHaveBeenCalled();

    await waitFor(() => expect(createSpy).toHaveBeenCalled());

    const [tokenArg, payloadArg, reasonArg] = createSpy.mock.calls[0];
    expect(tokenArg).toBe("token");
    expect(payloadArg.name).toBe("Lista corporativa");
    expect(reasonArg).toBe("Motivo válido");
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PriceLists from "../PriceLists";
import type { PriceList } from "../../../../services/api/pricing";

const dashboardMock = {
  enablePriceLists: true,
  selectedStore: { id: 1, name: "Sucursal Centro" },
  selectedStoreId: 1,
  formatCurrency: (value: number) => `$${value.toFixed(2)}`,
  pushToast: vi.fn(),
  setError: vi.fn(),
};

vi.mock("../../../../modules/dashboard/context/DashboardContext", () => ({
  useDashboard: () => dashboardMock,
}));

vi.mock("../../../../services/api/pricing", () => ({
  listPriceLists: vi.fn(),
  createPriceList: vi.fn(),
  updatePriceList: vi.fn(),
  deletePriceList: vi.fn(),
  createPriceListItem: vi.fn(),
  updatePriceListItem: vi.fn(),
  deletePriceListItem: vi.fn(),
  evaluatePrice: vi.fn(),
}));

vi.mock("../../../../utils/corporateReason", () => ({
  promptCorporateReason: vi.fn(() => "Motivo válido"),
}));

import * as pricingApi from "../../../../services/api/pricing";
import { promptCorporateReason } from "../../../../utils/corporateReason";

const mockedPricing = vi.mocked(pricingApi);
const mockedPrompt = vi.mocked(promptCorporateReason);

describe("PriceLists", () => {
  const sampleLists: PriceList[] = [
    {
      id: 10,
      name: "General",
      description: null,
      priority: 100,
      is_active: true,
      store_id: null,
      customer_id: null,
      starts_at: null,
      ends_at: null,
      scope: "global",
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
      items: [],
    },
    {
      id: 11,
      name: "Preferente",
      description: "Clientes frecuentes",
      priority: 50,
      is_active: true,
      store_id: 1,
      customer_id: null,
      starts_at: null,
      ends_at: null,
      scope: "store",
      created_at: "2024-01-02T00:00:00Z",
      updated_at: "2024-01-02T00:00:00Z",
      items: [
        {
          id: 201,
          price_list_id: 11,
          device_id: 501,
          price: 899.9,
          currency: "MXN",
          notes: "Descuento tienda",
          created_at: "2024-01-02T00:00:00Z",
          updated_at: "2024-01-02T00:00:00Z",
        },
      ],
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    dashboardMock.enablePriceLists = true;
    mockedPricing.listPriceLists.mockResolvedValue(sampleLists);
    mockedPricing.evaluatePrice.mockResolvedValue({
      device_id: 501,
      price_list_id: 11,
      scope: "store",
      price: 899.9,
      currency: "MXN",
    });
    mockedPrompt.mockReturnValue("Motivo válido");
  });

  it("muestra las listas existentes y permite seleccionar detalles", async () => {
    render(<PriceLists />);

    await waitFor(() => {
      expect(mockedPricing.listPriceLists).toHaveBeenCalledTimes(1);
    });

    expect(screen.getAllByRole("cell", { name: "General" })).not.toHaveLength(0);
    expect(screen.getAllByRole("cell", { name: "Preferente" })).not.toHaveLength(0);

    const preferentialRow = screen.getByRole("button", {
      name: /Preferente 50 Sucursal Activa/,
    });
    await userEvent.click(preferentialRow);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Preferente" })).toBeInTheDocument();
    });

    expect(screen.getByText("Descuento tienda")).toBeInTheDocument();
  });

  it("crea una nueva lista vinculada a la sucursal activa", async () => {
    render(<PriceLists />);
    await waitFor(() => expect(mockedPricing.listPriceLists).toHaveBeenCalled());

    const nameInput = screen.getByLabelText("Nombre");
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, "Lista VIP");

    const createButton = screen.getByRole("button", { name: /crear lista/i });
    await userEvent.click(createButton);

    await waitFor(() => {
      expect(mockedPricing.createPriceList).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Lista VIP",
          store_id: 1,
        }),
        "Motivo válido",
      );
    });
  });

  it("agrega un precio específico al seleccionar una lista", async () => {
    render(<PriceLists />);
    await waitFor(() => expect(mockedPricing.listPriceLists).toHaveBeenCalled());

    const deviceInput = screen.getByLabelText("ID de producto");
    await userEvent.clear(deviceInput);
    await userEvent.type(deviceInput, "601");

    const priceInput = screen.getByLabelText("Precio");
    await userEvent.clear(priceInput);
    await userEvent.type(priceInput, "799.5");

    const addButton = screen.getByRole("button", { name: /agregar precio/i });
    await userEvent.click(addButton);

    await waitFor(() => {
      expect(mockedPricing.createPriceListItem).toHaveBeenCalledWith(
        10,
        expect.objectContaining({ device_id: 601, price: 799.5 }),
        "Motivo válido",
      );
    });
  });
  it("permanece oculto cuando la bandera corporativa está desactivada", async () => {
    dashboardMock.enablePriceLists = false;
    render(<PriceLists />);

    expect(mockedPricing.listPriceLists).not.toHaveBeenCalled();
    expect(screen.queryByText("General")).not.toBeInTheDocument();

    dashboardMock.enablePriceLists = true;
  });
});
