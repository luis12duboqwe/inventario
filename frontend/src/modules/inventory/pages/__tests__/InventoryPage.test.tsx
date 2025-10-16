import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  Device,
  DeviceUpdateInput,
  LowStockDevice,
  Store,
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
  low_stock_threshold: 7,
});

const buildDevice = (): Device => ({
  id: 101,
  sku: "SKU-001",
  name: "Galaxy S24",
  quantity: 5,
  store_id: 1,
  unit_price: 15000,
  inventory_value: 75000,
  imei: "490154203237518",
  serial: "SERIAL-001",
  marca: "Samsung",
  modelo: "Galaxy S24",
  color: "Negro",
  capacidad_gb: 256,
  estado_comercial: "nuevo",
  proveedor: "Samsung",
  costo_unitario: 12000,
  margen_porcentaje: 20,
  garantia_meses: 12,
  lote: "L-001",
  fecha_compra: "2025-01-15",
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
  supplierBatchOverview: [],
  supplierBatchLoading: false,
  refreshSupplierBatchOverview: vi.fn(),
  lowStockThreshold: 7,
  updateLowStockThreshold: updateLowStockThresholdMock,
  refreshSummary: refreshSummaryMock,
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
  refreshSummaryMock.mockReset();
  promptCorporateReasonMock.mockReset();

  handleDeviceUpdateMock.mockResolvedValue();
  updateLowStockThresholdMock.mockResolvedValue();
  downloadInventoryReportMock.mockResolvedValue();
  downloadInventoryCsvMock.mockResolvedValue();

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
});
