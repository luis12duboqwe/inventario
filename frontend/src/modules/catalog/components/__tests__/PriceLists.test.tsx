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
