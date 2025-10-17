import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  Device,
  DeviceImportSummary,
  DeviceListFilters,
  DeviceUpdateInput,
  InventoryCurrentFilters,
  InventoryCurrentReport,
  InventoryMovementsFilters,
  InventoryMovementsReport,
  InventoryTopProductsFilters,
  InventoryValueFilters,
  InventoryValueReport,
  LowStockDevice,
  Store,
  TopProductsReport,
} from "../../../../api";
import type { useInventoryModule } from "../../hooks/useInventoryModule";

vi.mock("framer-motion", () => {
  const element = ({ children, ...rest }: { children?: React.ReactNode }) => (
    <div {...rest}>{children}</div>
  );
  const motionProxy = new Proxy(
    {},
    {
      get: () => element,
    },
  );
  return {
    __esModule: true,
    motion: motionProxy,
    AnimatePresence: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
  };
});

const pushToastMock = vi.fn();
const setErrorMock = vi.fn();
const setGlobalSearchTermMock = vi.fn();
const updateLowStockThresholdMock = vi.fn<(storeId: number, threshold: number) => Promise<void>>();
const handleDeviceUpdateMock = vi.fn<
  (deviceId: number, updates: DeviceUpdateInput, reason: string) => Promise<void>
>();
const downloadInventoryReportMock = vi.fn<(reason: string) => Promise<void>>();
const downloadInventoryCsvMock = vi.fn<(reason: string) => Promise<void>>();
const downloadInventoryCurrentCsvMock = vi.fn<
  (reason: string, filters: InventoryCurrentFilters) => Promise<void>
>();
const exportCatalogCsvMock = vi.fn<(filters: DeviceListFilters, reason: string) => Promise<void>>();
const importCatalogCsvMock = vi.fn<(file: unknown, reason: string) => Promise<DeviceImportSummary>>();
const downloadInventoryValueCsvMock = vi.fn<
  (reason: string, filters: InventoryValueFilters) => Promise<void>
>();
const downloadInventoryMovementsCsvMock = vi.fn<
  (reason: string, filters: InventoryMovementsFilters) => Promise<void>
>();
const downloadTopProductsCsvMock = vi.fn<
  (reason: string, filters: InventoryTopProductsFilters) => Promise<void>
>();
const refreshSummaryMock = vi.fn<() => Promise<void> | void>();
const promptCorporateReasonMock = vi.fn<(defaultReason: string) => string | null>();

const inventoryTableMock = vi.hoisted(() =>
  () => ({
    __esModule: true,
    default: ({
      devices,
      onEditDevice,
    }: {
      devices: Device[];
      onEditDevice?: (device: Device) => void;
    }) => (
      <div>
        {devices.map((device) => (
          <div key={device.id}>
            <span>{device.name}</span>
            {onEditDevice ? (
              <button type="button" onClick={() => onEditDevice(device)}>
                Editar ficha
              </button>
            ) : null}
          </div>
        ))}
      </div>
    ),
  })
);

const inventoryTableModuleId = vi.hoisted(() =>
  new URL("../../components/InventoryTable.tsx", import.meta.url).pathname
);

vi.mock("../components/InventoryTable", inventoryTableMock);
vi.mock("../components/InventoryTable.tsx", inventoryTableMock);
vi.mock("../../components/InventoryTable", inventoryTableMock);
vi.mock("../../components/InventoryTable.tsx", inventoryTableMock);
vi.mock(inventoryTableModuleId, inventoryTableMock);
vi.mock("/src/modules/inventory/components/InventoryTable", inventoryTableMock);
vi.mock("/src/modules/inventory/components/InventoryTable.tsx", inventoryTableMock);
vi.mock("../components/MovementForm", () => ({
  __esModule: true,
  default: () => <div data-testid="movement-form" />,
}));
vi.mock("../components/AdvancedSearch", () => ({
  __esModule: true,
  default: () => <div data-testid="advanced-search" />,
}));
vi.mock("../../../../utils/corporateReason", () => ({
  __esModule: true,
  promptCorporateReason: promptCorporateReasonMock,
}));
vi.mock("../../../../utils/corporateReason.ts", () => ({
  __esModule: true,
  promptCorporateReason: promptCorporateReasonMock,
}));
const moduleHeaderModuleId = vi.hoisted(() =>
  new URL("../../../components/ModuleHeader.tsx", import.meta.url).pathname
);

const mockModuleHeader = vi.hoisted(
  () =>
    () => ({
      __esModule: true,
      default: ({ title }: { title: string }) => (
        <header data-testid="module-header">
          <h1>{title}</h1>
        </header>
      ),
    })
);

vi.mock("../../../components/ModuleHeader", mockModuleHeader);
vi.mock("../../components/ModuleHeader", mockModuleHeader);
vi.mock("../../../components/ModuleHeader.tsx", mockModuleHeader);
vi.mock("../../components/ModuleHeader.tsx", mockModuleHeader);
vi.mock(moduleHeaderModuleId, mockModuleHeader);

const dashboardContextModuleId = vi.hoisted(() =>
  new URL("../../dashboard/context/DashboardContext.tsx", import.meta.url).pathname
);

const mockDashboardModule = vi.hoisted(
  () =>
    () => ({
      __esModule: true,
      useDashboard: () =>
        ({
          globalSearchTerm: "",
          setGlobalSearchTerm: setGlobalSearchTermMock,
          pushToast: pushToastMock,
          setError: setErrorMock,
        }) as ReturnType<typeof import("../../dashboard/context/DashboardContext").useDashboard>,
    })
);

vi.mock("../../dashboard/context/DashboardContext", mockDashboardModule);
vi.mock("../../../dashboard/context/DashboardContext", mockDashboardModule);
vi.mock("../../dashboard/context/DashboardContext.tsx", mockDashboardModule);
vi.mock("../../../dashboard/context/DashboardContext.tsx", mockDashboardModule);
vi.mock(dashboardContextModuleId, mockDashboardModule);

vi.stubGlobal(
  "matchMedia",
  vi.fn().mockImplementation(() => ({
    matches: false,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
);

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: globalThis.matchMedia,
});

type InventoryModuleState = ReturnType<typeof useInventoryModule>;

let moduleState: InventoryModuleState;

vi.mock("../../hooks/useInventoryModule", () => ({
  useInventoryModule: () => moduleState,
}));
vi.mock("../../hooks/useInventoryModule.ts", () => ({
  useInventoryModule: () => moduleState,
}));
vi.mock("../hooks/useInventoryModule", () => ({
  useInventoryModule: () => moduleState,
}));
vi.mock("../hooks/useInventoryModule.ts", () => ({
  useInventoryModule: () => moduleState,
}));
const useInventoryModuleId = vi.hoisted(() =>
  new URL("../../hooks/useInventoryModule.ts", import.meta.url).pathname
);
vi.mock(useInventoryModuleId, () => ({
  __esModule: true,
  useInventoryModule: () => moduleState,
}));

let InventoryPage: typeof import("../InventoryPage").default;

const buildStore = (): Store => ({
  id: 1,
  name: "Sucursal Centro",
  location: "CDMX",
  timezone: "America/Mexico_City",
  inventory_value: 72000,
  low_stock_threshold: 7,
});

const buildDevice = (): Device => ({
  id: 101,
  sku: "SKU-001",
  name: "Galaxy S24",
  quantity: 5,
  store_id: 1,
  unit_price: 15000,
  precio_venta: 15000,
  inventory_value: 75000,
  imei: "490154203237518",
  serial: "SERIAL-001",
  marca: "Samsung",
  modelo: "Galaxy S24",
  categoria: "Smartphones",
  condicion: "Nuevo",
  color: "Negro",
  capacidad_gb: 256,
  capacidad: "256 GB",
  estado_comercial: "nuevo",
  estado: "disponible",
  proveedor: "Samsung",
  costo_unitario: 12000,
  costo_compra: 12000,
  margen_porcentaje: 20,
  garantia_meses: 12,
  lote: "L-001",
  fecha_compra: "2025-01-15",
  fecha_ingreso: "2025-01-16",
  ubicacion: "Vitrina",
  descripcion: "Equipo de exhibición",
  imagen_url: "https://example.com/galaxy-s24.png",
});

const buildLowStockDevice = (): LowStockDevice => ({
  store_id: 1,
  store_name: "Sucursal Centro",
  device_id: 101,
  sku: "SKU-001",
  name: "Galaxy S24",
  quantity: 2,
  unit_price: 15000,
  inventory_value: 30000,
});

const buildInventoryCurrentReport = (): InventoryCurrentReport => ({
  stores: [
    {
      store_id: 1,
      store_name: "Sucursal Centro",
      device_count: 1,
      total_units: 5,
      total_value: 75000,
    },
  ],
  totals: {
    stores: 1,
    devices: 1,
    total_units: 5,
    total_value: 75000,
  },
});

const buildInventoryValueReport = (): InventoryValueReport => ({
  stores: [
    {
      store_id: 1,
      store_name: "Sucursal Centro",
      valor_total: 75000,
      valor_costo: 60000,
      margen_total: 15000,
    },
  ],
  totals: {
    valor_total: 75000,
    valor_costo: 60000,
    margen_total: 15000,
  },
});

const buildInventoryMovementsReport = (): InventoryMovementsReport => ({
  resumen: {
    total_movimientos: 2,
    total_unidades: 8,
    total_valor: 18000,
    por_tipo: [
      { tipo_movimiento: "entrada", total_cantidad: 5, total_valor: 9000 },
      { tipo_movimiento: "salida", total_cantidad: 3, total_valor: 9000 },
      { tipo_movimiento: "ajuste", total_cantidad: 0, total_valor: 0 },
    ],
  },
  periodos: [
    {
      periodo: "2025-03-01",
      tipo_movimiento: "entrada",
      total_cantidad: 5,
      total_valor: 9000,
    },
    {
      periodo: "2025-03-02",
      tipo_movimiento: "salida",
      total_cantidad: 3,
      total_valor: 9000,
    },
  ],
  movimientos: [
    {
      id: 1,
      tipo_movimiento: "entrada",
      cantidad: 5,
      valor_total: 9000,
      tienda_destino_id: 1,
      tienda_destino: "Sucursal Centro",
      tienda_origen_id: null,
      tienda_origen: null,
      comentario: "Reposición",
      usuario: "Admin General",
      fecha: new Date("2025-03-01T12:00:00Z").toISOString(),
    },
    {
      id: 2,
      tipo_movimiento: "salida",
      cantidad: 3,
      valor_total: 9000,
      tienda_destino_id: 1,
      tienda_destino: "Sucursal Centro",
      tienda_origen_id: null,
      tienda_origen: null,
      comentario: "Venta mostrador",
      usuario: "Admin General",
      fecha: new Date("2025-03-02T16:30:00Z").toISOString(),
    },
  ],
});

const buildTopProductsReport = (): TopProductsReport => ({
  items: [
    {
      device_id: 101,
      sku: "SKU-001",
      nombre: "Galaxy S24",
      store_id: 1,
      store_name: "Sucursal Centro",
      unidades_vendidas: 3,
      ingresos_totales: 45000,
      margen_estimado: 9000,
    },
  ],
  total_unidades: 3,
  total_ingresos: 45000,
});

const createModuleState = (): InventoryModuleState => ({
  token: "token-123",
  enableCatalogPro: true,
  stores: [buildStore()],
  selectedStoreId: 1,
  setSelectedStoreId: vi.fn(),
  selectedStore: buildStore(),
  devices: [buildDevice()],
  loading: false,
  totalDevices: 1,
  totalItems: 5,
  totalValue: 75000,
  formatCurrency: (value: number) => new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
  }).format(value),
  topStores: [
    {
      store_id: 1,
      store_name: "Sucursal Centro",
      device_count: 1,
      total_units: 5,
      total_value: 75000,
    },
  ],
  lowStockDevices: [buildLowStockDevice()],
  handleMovement: vi.fn(),
  handleDeviceUpdate: handleDeviceUpdateMock,
  backupHistory: [],
  updateStatus: null,
  lastInventoryRefresh: new Date("2025-02-28T10:00:00.000Z"),
  downloadInventoryReport: downloadInventoryReportMock,
  downloadInventoryCsv: downloadInventoryCsvMock,
  exportCatalogCsv: exportCatalogCsvMock,
  importCatalogCsv: importCatalogCsvMock,
  supplierBatchOverview: [],
  supplierBatchLoading: false,
  refreshSupplierBatchOverview: vi.fn(),
  lowStockThreshold: 7,
  updateLowStockThreshold: updateLowStockThresholdMock,
  refreshSummary: refreshSummaryMock,
  storeValuationSnapshot: {
    storeId: 1,
    storeName: "Sucursal Centro",
    registeredValue: 72000,
    calculatedValue: 75000,
    difference: 3000,
    differenceAbs: 3000,
    differencePercent: (3000 / 72000) * 100,
    hasRelevantDifference: true,
  },
  fetchInventoryCurrentReport: vi.fn().mockResolvedValue(buildInventoryCurrentReport()),
  fetchInventoryValueReport: vi.fn().mockResolvedValue(buildInventoryValueReport()),
  fetchInventoryMovementsReport: vi.fn().mockResolvedValue(buildInventoryMovementsReport()),
  fetchTopProductsReport: vi.fn().mockResolvedValue(buildTopProductsReport()),
  downloadInventoryCurrentCsv: downloadInventoryCurrentCsvMock,
  downloadInventoryValueCsv: downloadInventoryValueCsvMock,
  downloadInventoryMovementsCsv: downloadInventoryMovementsCsvMock,
  downloadTopProductsCsv: downloadTopProductsCsvMock,
});

const openTab = async (user: ReturnType<typeof userEvent.setup>, tabName: RegExp) => {
  const tab = await screen.findByRole("tab", { name: tabName });
  await user.click(tab);
};

const renderInventoryPage = async () => {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/dashboard/inventory"]}>
      <InventoryPage />
    </MemoryRouter>
  );
  return user;
};

beforeAll(async () => {
  const module = await import("../InventoryPage");
  InventoryPage = module.default;
});

beforeEach(() => {
  pushToastMock.mockReset();
  setErrorMock.mockReset();
  setGlobalSearchTermMock.mockReset();
  updateLowStockThresholdMock.mockReset();
  handleDeviceUpdateMock.mockReset();
  downloadInventoryReportMock.mockReset();
  downloadInventoryCsvMock.mockReset();
  downloadInventoryCurrentCsvMock.mockReset();
  exportCatalogCsvMock.mockReset();
  importCatalogCsvMock.mockReset();
  downloadInventoryValueCsvMock.mockReset();
  downloadInventoryMovementsCsvMock.mockReset();
  downloadTopProductsCsvMock.mockReset();
  refreshSummaryMock.mockReset();
  promptCorporateReasonMock.mockReset();

  handleDeviceUpdateMock.mockResolvedValue();
  updateLowStockThresholdMock.mockResolvedValue();
  downloadInventoryReportMock.mockResolvedValue();
  downloadInventoryCsvMock.mockResolvedValue();
  downloadInventoryCurrentCsvMock.mockResolvedValue();
  exportCatalogCsvMock.mockResolvedValue();
  importCatalogCsvMock.mockResolvedValue({ created: 0, updated: 0, skipped: 0, errors: [] });
  downloadInventoryValueCsvMock.mockResolvedValue();
  downloadInventoryMovementsCsvMock.mockResolvedValue();
  downloadTopProductsCsvMock.mockResolvedValue();

  moduleState = createModuleState();
});

describe("InventoryPage", () => {
  it("permite editar un dispositivo y envía los cambios", async () => {
    const user = await renderInventoryPage();

    await openTab(user, /movimientos/i);

    const editButton = await screen.findByRole("button", { name: /editar ficha/i });
    await user.click(editButton);

    const dialog = await screen.findByRole("dialog", { name: /editar sku-001/i });
    const dialogScope = within(dialog);
    expect(dialog).toBeInTheDocument();

    const nameInput = dialogScope.getByLabelText("Nombre comercial");
    await user.clear(nameInput);
    await user.type(nameInput, "Galaxy S24 Ultra");

    const reasonInput = dialogScope.getByLabelText("Motivo corporativo");
    await user.type(reasonInput, "Actualización de catálogo");

    const saveButton = dialogScope.getByRole("button", { name: "Guardar cambios" });
    await user.click(saveButton);

    await waitFor(() => {
      expect(handleDeviceUpdateMock).toHaveBeenCalledWith(
        101,
        expect.objectContaining({ name: "Galaxy S24 Ultra" }),
        "Actualización de catálogo",
      );
    });

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  it("actualiza el umbral de stock bajo y muestra confirmación", async () => {
    const user = await renderInventoryPage();

    await openTab(user, /alertas/i);

    const thresholdInput = await screen.findByRole("spinbutton");
    await user.clear(thresholdInput);
    await user.type(thresholdInput, "9");

    const saveButton = screen.getByRole("button", { name: "Guardar umbral" });
    await user.click(saveButton);

    await waitFor(() => {
      expect(updateLowStockThresholdMock).toHaveBeenCalledWith(1, 9);
    });

    expect(pushToastMock).toHaveBeenCalledWith(
      expect.objectContaining({
        message: "Umbral de stock bajo actualizado",
        variant: "success",
      }),
    );
  });

  it("solicita un motivo y descarga el PDF de inventario", async () => {
    promptCorporateReasonMock.mockReturnValue("Inventario semanal");

    const user = await renderInventoryPage();

    await openTab(user, /movimientos/i);

    const downloadButton = await screen.findByRole("button", { name: "Descargar PDF" });
    await user.click(downloadButton);

    expect(promptCorporateReasonMock).toHaveBeenCalledWith("Descarga inventario Sucursal Centro");

    await waitFor(() => {
      expect(downloadInventoryReportMock).toHaveBeenCalledWith("Inventario semanal");
    });

    expect(pushToastMock).toHaveBeenCalledWith(
      expect.objectContaining({
        message: "PDF de inventario descargado",
        variant: "success",
      }),
    );
  });

  it("reporta el error al fallar la descarga del PDF", async () => {
    promptCorporateReasonMock.mockReturnValue("Motivo válido");
    const errorMessage = "El motivo corporativo enviado no cumple con la longitud mínima de 5 caracteres.";
    downloadInventoryReportMock.mockRejectedValueOnce(new Error(errorMessage));

    const user = await renderInventoryPage();

    await openTab(user, /movimientos/i);

    const downloadButton = await screen.findByRole("button", { name: "Descargar PDF" });
    await user.click(downloadButton);

    await waitFor(() => {
      expect(downloadInventoryReportMock).toHaveBeenCalled();
    });

    expect(setErrorMock).toHaveBeenCalledWith(errorMessage);
    expect(pushToastMock).toHaveBeenCalledWith(
      expect.objectContaining({ message: errorMessage, variant: "error" }),
    );
  });

  it("muestra los reportes de inventario y habilita exportaciones", async () => {
    promptCorporateReasonMock.mockReturnValue("Reporte inventario");

    const user = await renderInventoryPage();

    await openTab(user, /reportes/i);

    expect(await screen.findByText(/Reportes y estadísticas/i)).toBeInTheDocument();
    expect(screen.getByText(/Existencias actuales/i)).toBeInTheDocument();

    const existencesSection = screen.getByRole("heading", { name: /Existencias actuales/i }).closest("section");
    const valueSection = screen.getByRole("heading", { name: /Valor total del inventario/i }).closest("section");
    const movementsSection = screen.getByRole("heading", { name: /Movimientos por periodo/i }).closest("section");
    const topProductsSection = screen.getByRole("heading", { name: /Productos más vendidos/i }).closest("section");

    expect(existencesSection).not.toBeNull();
    expect(valueSection).not.toBeNull();
    expect(movementsSection).not.toBeNull();
    expect(topProductsSection).not.toBeNull();

    const existencesButton = within(existencesSection as HTMLElement).getByRole("button", {
      name: /Exportar CSV/i,
    });
    await user.click(existencesButton);
    await waitFor(() => {
      expect(downloadInventoryCurrentCsvMock).toHaveBeenCalledWith(
        "Reporte inventario",
        expect.any(Object),
      );
    });

    const valuationButton = within(valueSection as HTMLElement).getByRole("button", { name: /Exportar CSV/i });
    await user.click(valuationButton);
    await waitFor(() => {
      expect(downloadInventoryValueCsvMock).toHaveBeenCalledWith("Reporte inventario", expect.any(Object));
    });

    const movementsButton = within(movementsSection as HTMLElement).getByRole("button", {
      name: /Exportar CSV/i,
    });
    await user.click(movementsButton);
    await waitFor(() => {
      expect(downloadInventoryMovementsCsvMock).toHaveBeenCalledWith(
        "Reporte inventario",
        expect.any(Object),
      );
    });

    const topProductsButton = within(topProductsSection as HTMLElement).getByRole("button", {
      name: /Exportar CSV/i,
    });
    await user.click(topProductsButton);
    await waitFor(() => {
      expect(downloadTopProductsCsvMock).toHaveBeenCalledWith(
        "Reporte inventario",
        expect.any(Object),
      );
    });
  });
});
