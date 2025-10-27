import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { getApiBaseUrl } from "../../../../config/api";

import type {
  Device,
  DeviceImportSummary,
  DeviceListFilters,
  DeviceUpdateInput,
  InventoryCurrentFilters,
  InventoryCurrentReport,
  InventoryImportHistoryEntry,
  InventoryMovementsFilters,
  InventoryMovementsReport,
  InventorySmartImportPreview,
  InventorySmartImportResponse,
  InventorySmartImportResult,
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
const downloadInventoryCurrentPdfMock = vi.fn<
  (reason: string, filters: InventoryCurrentFilters) => Promise<void>
>();
const downloadInventoryCurrentXlsxMock = vi.fn<
  (reason: string, filters: InventoryCurrentFilters) => Promise<void>
>();
const exportCatalogCsvMock = vi.fn<(filters: DeviceListFilters, reason: string) => Promise<void>>();
const importCatalogCsvMock = vi.fn<(file: unknown, reason: string) => Promise<DeviceImportSummary>>();
const downloadInventoryValueCsvMock = vi.fn<
  (reason: string, filters: InventoryValueFilters) => Promise<void>
>();
const downloadInventoryValuePdfMock = vi.fn<
  (reason: string, filters: InventoryValueFilters) => Promise<void>
>();
const downloadInventoryValueXlsxMock = vi.fn<
  (reason: string, filters: InventoryValueFilters) => Promise<void>
>();
const downloadInventoryMovementsCsvMock = vi.fn<
  (reason: string, filters: InventoryMovementsFilters) => Promise<void>
>();
const downloadInventoryMovementsPdfMock = vi.fn<
  (reason: string, filters: InventoryMovementsFilters) => Promise<void>
>();
const downloadInventoryMovementsXlsxMock = vi.fn<
  (reason: string, filters: InventoryMovementsFilters) => Promise<void>
>();
const downloadTopProductsCsvMock = vi.fn<
  (reason: string, filters: InventoryTopProductsFilters) => Promise<void>
>();
const downloadTopProductsPdfMock = vi.fn<
  (reason: string, filters: InventoryTopProductsFilters) => Promise<void>
>();
const downloadTopProductsXlsxMock = vi.fn<
  (reason: string, filters: InventoryTopProductsFilters) => Promise<void>
>();
const refreshSummaryMock = vi.fn<() => Promise<void> | void>();
const refreshRecentMovementsMock = vi.fn<() => Promise<void>>();
const smartImportInventoryMock = vi.fn<
  (
    file: File,
    reason: string,
    options: { commit?: boolean; overrides?: Record<string, string> },
  ) => Promise<InventorySmartImportResponse>
>();
const fetchSmartImportHistoryMock = vi.fn<
  (limit?: number) => Promise<InventoryImportHistoryEntry[]>
>();
const fetchIncompleteDevicesMock = vi.fn<
  (storeId?: number, limit?: number) => Promise<Device[]>
>();
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
  new URL("../../../shared/components/ModuleHeader.tsx", import.meta.url).pathname
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

vi.mock("../../../shared/components/ModuleHeader", mockModuleHeader);
vi.mock("../../shared/components/ModuleHeader", mockModuleHeader);
vi.mock("../../../shared/components/ModuleHeader.tsx", mockModuleHeader);
vi.mock("../../shared/components/ModuleHeader.tsx", mockModuleHeader);
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

const API_BASE_URL = (import.meta.env.VITE_API_URL?.trim() ?? "") || getApiBaseUrl();

const buildImageUrl = (path: string): string => new URL(path, API_BASE_URL).toString();

const buildDevice = (): Device => ({
  id: 101,
  sku: "SKU-001",
  name: "Galaxy S24",
  quantity: 5,
  store_id: 1,
  unit_price: 15000,
  precio_venta: 15000,
  inventory_value: 75000,
  completo: true,
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
  imagen_url: buildImageUrl("/media/devices/galaxy-s24.png"),
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
      sucursal_destino_id: 1,
      sucursal_destino: "Sucursal Centro",
      sucursal_origen_id: null,
      sucursal_origen: null,
      comentario: "Reposición",
      usuario: "Admin General",
      fecha: new Date("2025-03-01T12:00:00Z").toISOString(),
    },
    {
      id: 2,
      tipo_movimiento: "salida",
      cantidad: 3,
      valor_total: 9000,
      sucursal_destino_id: 1,
      sucursal_destino: "Sucursal Centro",
      sucursal_origen_id: null,
      sucursal_origen: null,
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

const buildSmartPreview = (): InventorySmartImportPreview => ({
  columnas: [
    {
      campo: "marca",
      encabezado_origen: "Marca",
      estado: "ok",
      tipo_dato: "texto",
      ejemplos: ["Samsung"],
    },
    {
      campo: "modelo",
      encabezado_origen: "Modelo",
      estado: "ok",
      tipo_dato: "texto",
      ejemplos: ["Galaxy S24"],
    },
    {
      campo: "imei",
      encabezado_origen: null,
      estado: "falta",
      tipo_dato: undefined,
      ejemplos: [],
    },
    {
      campo: "serial",
      encabezado_origen: "Identificador",
      estado: "pendiente",
      tipo_dato: "texto",
      ejemplos: ["990000000000001"],
    },
    {
      campo: "estado",
      encabezado_origen: "Disponible",
      estado: "ok",
      tipo_dato: "booleano",
      ejemplos: ["Sí"],
    },
  ],
  columnas_detectadas: {
    marca: "Marca",
    modelo: "Modelo",
    imei: null,
    serial: "Identificador",
    estado: "Disponible",
  },
  columnas_faltantes: ["imei"],
  total_filas: 2,
  registros_incompletos_estimados: 1,
  advertencias: ["Columnas faltantes: imei"],
  patrones_sugeridos: {
    marca: "marca",
    modelo: "modelo",
    identificador: "serial",
  },
});

const buildSmartResult = (): InventorySmartImportResult => ({
  total_procesados: 2,
  nuevos: 1,
  actualizados: 1,
  registros_incompletos: 1,
  columnas_faltantes: ["imei"],
  advertencias: ["Fila 1: sin IMEI detectado"],
  tiendas_nuevas: ["Sucursal Norte"],
  duracion_segundos: 4.8,
  resumen:
    "📦 Resultado de importación:\n- Total procesados: 2\n- Nuevos productos: 1\n- Actualizados: 1\n- Columnas faltantes: imei\n- Registros incompletos: 1",
});

const buildImportHistoryEntry = (): InventoryImportHistoryEntry => ({
  id: 1,
  nombre_archivo: "inventario.xlsx",
  fecha: new Date("2025-02-21T12:00:00Z").toISOString(),
  columnas_detectadas: {
    marca: "Marca",
    modelo: "Modelo",
    imei: "IMEI",
  },
  registros_incompletos: 1,
  total_registros: 2,
  nuevos: 1,
  actualizados: 1,
  advertencias: ["IMEI faltante en fila 1"],
  duracion_segundos: 3.2,
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
  stockByCategory: [
    { label: "Smartphones", value: 12 },
    { label: "Tablets", value: 4 },
  ],
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
  recentMovements: buildInventoryMovementsReport().movimientos,
  recentMovementsLoading: false,
  refreshRecentMovements: refreshRecentMovementsMock,
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
  downloadInventoryCurrentPdf: downloadInventoryCurrentPdfMock,
  downloadInventoryCurrentXlsx: downloadInventoryCurrentXlsxMock,
  downloadInventoryValueCsv: downloadInventoryValueCsvMock,
  downloadInventoryValuePdf: downloadInventoryValuePdfMock,
  downloadInventoryValueXlsx: downloadInventoryValueXlsxMock,
  downloadInventoryMovementsCsv: downloadInventoryMovementsCsvMock,
  downloadInventoryMovementsPdf: downloadInventoryMovementsPdfMock,
  downloadInventoryMovementsXlsx: downloadInventoryMovementsXlsxMock,
  downloadTopProductsCsv: downloadTopProductsCsvMock,
  downloadTopProductsPdf: downloadTopProductsPdfMock,
  downloadTopProductsXlsx: downloadTopProductsXlsxMock,
  smartImportInventory: smartImportInventoryMock,
  fetchSmartImportHistory: fetchSmartImportHistoryMock,
  fetchIncompleteDevices: fetchIncompleteDevicesMock,
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
  downloadInventoryCurrentPdfMock.mockReset();
  downloadInventoryCurrentXlsxMock.mockReset();
  exportCatalogCsvMock.mockReset();
  importCatalogCsvMock.mockReset();
  downloadInventoryValueCsvMock.mockReset();
  downloadInventoryValuePdfMock.mockReset();
  downloadInventoryValueXlsxMock.mockReset();
  downloadInventoryMovementsCsvMock.mockReset();
  downloadInventoryMovementsPdfMock.mockReset();
  downloadInventoryMovementsXlsxMock.mockReset();
  downloadTopProductsCsvMock.mockReset();
  downloadTopProductsPdfMock.mockReset();
  downloadTopProductsXlsxMock.mockReset();
  refreshSummaryMock.mockReset();
  refreshRecentMovementsMock.mockReset();
  smartImportInventoryMock.mockReset();
  fetchSmartImportHistoryMock.mockReset();
  fetchIncompleteDevicesMock.mockReset();
  promptCorporateReasonMock.mockReset();

  handleDeviceUpdateMock.mockResolvedValue();
  updateLowStockThresholdMock.mockResolvedValue();
  downloadInventoryReportMock.mockResolvedValue();
  downloadInventoryCsvMock.mockResolvedValue();
  downloadInventoryCurrentCsvMock.mockResolvedValue();
  downloadInventoryCurrentPdfMock.mockResolvedValue();
  downloadInventoryCurrentXlsxMock.mockResolvedValue();
  exportCatalogCsvMock.mockResolvedValue();
  importCatalogCsvMock.mockResolvedValue({ created: 0, updated: 0, skipped: 0, errors: [] });
  downloadInventoryValueCsvMock.mockResolvedValue();
  downloadInventoryValuePdfMock.mockResolvedValue();
  downloadInventoryValueXlsxMock.mockResolvedValue();
  downloadInventoryMovementsCsvMock.mockResolvedValue();
  downloadInventoryMovementsPdfMock.mockResolvedValue();
  downloadInventoryMovementsXlsxMock.mockResolvedValue();
  downloadTopProductsCsvMock.mockResolvedValue();
  downloadTopProductsPdfMock.mockResolvedValue();
  downloadTopProductsXlsxMock.mockResolvedValue();
  refreshRecentMovementsMock.mockResolvedValue();
  smartImportInventoryMock.mockResolvedValue({ preview: buildSmartPreview(), resultado: null });
  fetchSmartImportHistoryMock.mockResolvedValue([]);
  fetchIncompleteDevicesMock.mockResolvedValue([]);

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

    await waitFor(() => {
      expect(fetchIncompleteDevicesMock).toHaveBeenCalledWith(1, 200);
    });
    expect(refreshSummaryMock).toHaveBeenCalled();
  });

  it("muestra el stock por categoría con totales visibles", async () => {
    await renderInventoryPage();

    const heading = await screen.findByRole("heading", { name: /Stock por categoría/i });
    const section = heading.closest("section");
    expect(section).not.toBeNull();

    const sectionScope = within(section as HTMLElement);
    expect(sectionScope.getByText(/Total 16 uds/i)).toBeInTheDocument();

    const categoryItems = sectionScope.getAllByRole("listitem");
    expect(categoryItems).toHaveLength(2);
    expect(categoryItems[0]).toHaveTextContent(/Smartphones/i);
    expect(categoryItems[0]).toHaveTextContent(/12 uds/i);
    expect(categoryItems[1]).toHaveTextContent(/Tablets/i);
  });

  it("despliega los últimos movimientos y permite actualizarlos", async () => {
    const user = await renderInventoryPage();

    const heading = await screen.findByRole("heading", { name: /Últimos movimientos/i });
    const section = heading.closest("section");
    expect(section).not.toBeNull();

    const sectionScope = within(section as HTMLElement);
    expect(sectionScope.getByText(/Reposición/i)).toBeInTheDocument();
    expect(sectionScope.getByText(/Venta mostrador/i)).toBeInTheDocument();

    const refreshButton = sectionScope.getByRole("button", { name: /Actualizar/i });
    await user.click(refreshButton);
    expect(refreshRecentMovementsMock).toHaveBeenCalled();
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

  it("analiza y confirma la importación inteligente", async () => {
    const preview = buildSmartPreview();
    const previewWithOverrides: InventorySmartImportPreview = {
      ...preview,
      columnas: preview.columnas.map((column) =>
        column.campo === "imei"
          ? {
              ...column,
              encabezado_origen: "Identificador",
              estado: "ok",
              ejemplos: ["990000000000001"],
            }
          : column,
      ),
      columnas_detectadas: { ...preview.columnas_detectadas, imei: "Identificador" },
      columnas_faltantes: [],
      registros_incompletos_estimados: 0,
      advertencias: [],
    };
    const result = buildSmartResult();

    smartImportInventoryMock
      .mockResolvedValueOnce({ preview, resultado: null })
      .mockResolvedValueOnce({ preview: previewWithOverrides, resultado: null })
      .mockResolvedValueOnce({ preview: previewWithOverrides, resultado: result });

    const historyEntry = buildImportHistoryEntry();
    fetchSmartImportHistoryMock.mockResolvedValue([historyEntry]);
    promptCorporateReasonMock.mockReturnValue("Importación inventario inteligente");

    const user = await renderInventoryPage();

    await openTab(user, /búsqueda avanzada/i);

    expect(await screen.findByText(/inventario\.xlsx/i)).toBeInTheDocument();

    const fileInput = screen.getByLabelText(/Archivo Excel o CSV/i) as HTMLInputElement;
    const file = new File([
      "Sucursal,Dispositivo,Identificador,Color,Cantidad,Precio\n",
      "Sucursal Norte,iPhone 14,990000000000001,Negro,2,18999\n",
    ], "inventario.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    await user.upload(fileInput, file);

    const analyzeButton = await screen.findByRole("button", { name: /Analizar estructura/i });
    await user.click(analyzeButton);

    await waitFor(() => {
      expect(smartImportInventoryMock).toHaveBeenNthCalledWith(1, file, "Importación inventario inteligente", {
        commit: false,
        overrides: {},
      });
    });

    expect(await screen.findByText(/Columnas faltantes: imei/i)).toBeInTheDocument();

    const imeiCell = await screen.findByText(/^imei$/i);
    const imeiRow = imeiCell.closest("tr") as HTMLElement;
    const overrideSelect = within(imeiRow).getByRole("combobox");
    await user.selectOptions(overrideSelect, "Identificador");

    expect(screen.getByText(/Reanaliza el archivo/i)).toBeInTheDocument();

    await user.click(analyzeButton);

    await waitFor(() => {
      expect(smartImportInventoryMock).toHaveBeenNthCalledWith(2, file, "Importación inventario inteligente", {
        commit: false,
        overrides: { imei: "Identificador" },
      });
    });

    expect(
      await screen.findByText(/Todas las columnas clave fueron identificadas./i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Reanaliza el archivo/i)).not.toBeInTheDocument();

    const importButton = screen.getByRole("button", { name: /Importar desde Excel/i });
    await user.click(importButton);

    await waitFor(() => {
      expect(smartImportInventoryMock).toHaveBeenNthCalledWith(3, file, "Importación inventario inteligente", {
        commit: true,
        overrides: { imei: "Identificador" },
      });
    });

    await waitFor(() => {
      expect(fetchSmartImportHistoryMock).toHaveBeenCalledTimes(2);
    });
    await waitFor(() => {
      expect(fetchIncompleteDevicesMock).toHaveBeenCalledWith(1, 200);
    });
    expect(refreshSummaryMock).toHaveBeenCalled();

    expect(await screen.findByText(/Tiempo estimado: 4\.8 segundos/)).toBeInTheDocument();
    expect(screen.getByText(/Tiendas creadas automáticamente/i)).toHaveTextContent("Sucursal Norte");
    expect(pushToastMock).toHaveBeenCalledWith(
      expect.objectContaining({ message: "Importación inteligente completada.", variant: "success" }),
    );
  });

  it("refresca las correcciones pendientes y permite editar un registro incompleto", async () => {
    const pendingDevice: Device = {
      ...buildDevice(),
      id: 202,
      sku: "SKU-002",
      name: "iPhone 14",
      marca: "",
      capacidad: null,
      capacidad_gb: null,
      imei: "",
      proveedor: null,
      ubicacion: null,
      completo: false,
    };
    fetchIncompleteDevicesMock.mockResolvedValue([pendingDevice]);

    const user = await renderInventoryPage();

    await openTab(user, /correcciones pendientes/i);

    await waitFor(() => {
      expect(fetchIncompleteDevicesMock).toHaveBeenCalledWith(1, 200);
    });

    const correctionsSection = screen.getByRole("heading", { name: /Correcciones pendientes/i }).closest("section");
    expect(correctionsSection).not.toBeNull();
    const correctionsScope = within(correctionsSection as HTMLElement);

    expect(await correctionsScope.findByText(/iPhone 14/i)).toBeInTheDocument();
    const deviceRow = correctionsScope.getByText(/iPhone 14/i).closest("tr") as HTMLElement;
    const missingScope = within(deviceRow);
    expect(missingScope.getByText(/Marca/)).toBeInTheDocument();
    expect(missingScope.getByText(/IMEI/)).toBeInTheDocument();

    const refreshButton = correctionsScope.getByRole("button", { name: "Actualizar" });
    await user.click(refreshButton);
    await waitFor(() => {
      expect(fetchIncompleteDevicesMock).toHaveBeenCalledTimes(2);
    });

    const completeButton = correctionsScope.getByRole("button", { name: /Completar datos/i });
    await user.click(completeButton);

    const dialog = await screen.findByRole("dialog", { name: /Editar SKU-002/i });
    expect(dialog).toBeInTheDocument();
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

    const existencesCsvButton = within(existencesSection as HTMLElement).getByRole("button", {
      name: /^CSV$/i,
    });
    await user.click(existencesCsvButton);
    await waitFor(() => {
      expect(downloadInventoryCurrentCsvMock).toHaveBeenCalledWith(
        "Reporte inventario",
        expect.any(Object),
      );
    });

    const existencesPdfButton = within(existencesSection as HTMLElement).getByRole("button", {
      name: /^PDF$/i,
    });
    await user.click(existencesPdfButton);
    await waitFor(() => {
      expect(downloadInventoryCurrentPdfMock).toHaveBeenCalledWith(
        "Reporte inventario",
        expect.any(Object),
      );
    });

    const existencesExcelButton = within(existencesSection as HTMLElement).getByRole("button", {
      name: /^Excel$/i,
    });
    await user.click(existencesExcelButton);
    await waitFor(() => {
      expect(downloadInventoryCurrentXlsxMock).toHaveBeenCalledWith(
        "Reporte inventario",
        expect.any(Object),
      );
    });

    const valuationCsvButton = within(valueSection as HTMLElement).getByRole("button", { name: /^CSV$/i });
    await user.click(valuationCsvButton);
    await waitFor(() => {
      expect(downloadInventoryValueCsvMock).toHaveBeenCalledWith("Reporte inventario", expect.any(Object));
    });

    const valuationPdfButton = within(valueSection as HTMLElement).getByRole("button", { name: /^PDF$/i });
    await user.click(valuationPdfButton);
    await waitFor(() => {
      expect(downloadInventoryValuePdfMock).toHaveBeenCalledWith(
        "Reporte inventario",
        expect.any(Object),
      );
    });

    const valuationExcelButton = within(valueSection as HTMLElement).getByRole("button", { name: /^Excel$/i });
    await user.click(valuationExcelButton);
    await waitFor(() => {
      expect(downloadInventoryValueXlsxMock).toHaveBeenCalledWith(
        "Reporte inventario",
        expect.any(Object),
      );
    });

    const movementsCsvButton = within(movementsSection as HTMLElement).getByRole("button", {
      name: /^CSV$/i,
    });
    await user.click(movementsCsvButton);
    await waitFor(() => {
      expect(downloadInventoryMovementsCsvMock).toHaveBeenCalledWith(
        "Reporte inventario",
        expect.any(Object),
      );
    });

    const movementsPdfButton = within(movementsSection as HTMLElement).getByRole("button", {
      name: /^PDF$/i,
    });
    await user.click(movementsPdfButton);
    await waitFor(() => {
      expect(downloadInventoryMovementsPdfMock).toHaveBeenCalledWith(
        "Reporte inventario",
        expect.any(Object),
      );
    });

    const movementsExcelButton = within(movementsSection as HTMLElement).getByRole("button", {
      name: /^Excel$/i,
    });
    await user.click(movementsExcelButton);
    await waitFor(() => {
      expect(downloadInventoryMovementsXlsxMock).toHaveBeenCalledWith(
        "Reporte inventario",
        expect.any(Object),
      );
    });

    const topProductsCsvButton = within(topProductsSection as HTMLElement).getByRole("button", {
      name: /^CSV$/i,
    });
    await user.click(topProductsCsvButton);
    await waitFor(() => {
      expect(downloadTopProductsCsvMock).toHaveBeenCalledWith(
        "Reporte inventario",
        expect.any(Object),
      );
    });

    const topProductsPdfButton = within(topProductsSection as HTMLElement).getByRole("button", {
      name: /^PDF$/i,
    });
    await user.click(topProductsPdfButton);
    await waitFor(() => {
      expect(downloadTopProductsPdfMock).toHaveBeenCalledWith(
        "Reporte inventario",
        expect.any(Object),
      );
    });

    const topProductsExcelButton = within(topProductsSection as HTMLElement).getByRole("button", {
      name: /^Excel$/i,
    });
    await user.click(topProductsExcelButton);
    await waitFor(() => {
      expect(downloadTopProductsXlsxMock).toHaveBeenCalledWith(
        "Reporte inventario",
        expect.any(Object),
      );
    });
  });
});
