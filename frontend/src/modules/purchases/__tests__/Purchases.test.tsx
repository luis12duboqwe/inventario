import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import Purchases from "../Purchases";
import type {
  PurchaseOrder,
  PurchaseReturn,
  PurchaseSuggestionsResponse,
  Store,
} from "../../../api";

const originalCreateObjectURL = URL.createObjectURL;
const originalRevokeObjectURL = URL.revokeObjectURL;

vi.mock("../../../auth/useAuth", () => ({
  useAuth: () => ({ accessToken: "token" }),
}));

const createPurchaseOrderFromSuggestionMock = vi.hoisted(() => vi.fn());
const getPurchaseSuggestionsMock = vi.hoisted(() =>
  vi.fn<[], Promise<PurchaseSuggestionsResponse>>()
);
const getStoresMock = vi.hoisted(() => vi.fn<[], Promise<Store[]>>());
const listPurchaseOrdersMock = vi.hoisted(() =>
  vi.fn<[], Promise<PurchaseOrder[]>>()
);
const registerPurchaseReturnMock = vi.hoisted(() =>
  vi.fn<[], Promise<PurchaseReturn>>()
);

vi.mock("../../../api", async (importOriginal) => {
  const mod = await importOriginal<typeof import("../../../api")>();
  return {
    ...mod,
    createPurchaseOrderFromSuggestion: createPurchaseOrderFromSuggestionMock,
    getPurchaseSuggestions: getPurchaseSuggestionsMock,
    getStores: getStoresMock,
    listPurchaseOrders: listPurchaseOrdersMock,
    registerPurchaseReturn: registerPurchaseReturnMock,
  };
});

const promptCorporateReasonMock = vi.hoisted(() => vi.fn());
vi.mock("../../../utils/corporateReason", () => ({
  promptCorporateReason: promptCorporateReasonMock,
}));

beforeAll(() => {
  Object.defineProperty(URL, "createObjectURL", {
    configurable: true,
    value: vi.fn(() => "blob:url"),
  });
  Object.defineProperty(URL, "revokeObjectURL", {
    configurable: true,
    value: vi.fn(),
  });
});

afterEach(() => {
  vi.clearAllMocks();
});

afterAll(() => {
  Object.defineProperty(URL, "createObjectURL", {
    configurable: true,
    value: originalCreateObjectURL,
  });
  Object.defineProperty(URL, "revokeObjectURL", {
    configurable: true,
    value: originalRevokeObjectURL,
  });
});

describe("Purchases", () => {
  it("permite registrar una devolución a proveedor y genera comprobante", async () => {
    getPurchaseSuggestionsMock.mockResolvedValue({
      generated_at: new Date().toISOString(),
      lookback_days: 30,
      planning_horizon_days: 7,
      minimum_stock: 5,
      total_items: 0,
      stores: [],
    });

    getStoresMock.mockResolvedValue([
      {
        id: 1,
        name: "Sucursal Norte",
        code: "NOR",
        status: "activa",
        location: "MX",
        phone: null,
        manager: null,
        timezone: "America/Mexico_City",
        inventory_value: 0,
        created_at: new Date().toISOString(),
      },
    ]);

    listPurchaseOrdersMock.mockResolvedValue([
      {
        id: 77,
        store_id: 1,
        supplier: "Proveedor Central",
        status: "COMPLETADA",
        notes: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        created_by_id: null,
        closed_at: null,
        items: [
          {
            id: 501,
            purchase_order_id: 77,
            device_id: 2001,
            quantity_ordered: 5,
            quantity_received: 5,
            unit_cost: 90,
          },
        ],
        returns: [],
      },
    ]);

    registerPurchaseReturnMock.mockResolvedValue({
      id: 900,
      purchase_order_id: 77,
      device_id: 2001,
      quantity: 2,
      reason: "Proveedor defectuoso",
      reason_category: "defecto",
      disposition: "defectuoso",
      warehouse_id: null,
      supplier_ledger_entry_id: 10,
      corporate_reason: "Motivo corporativo",
      credit_note_amount: 180,
      processed_by_id: 5,
      approved_by_id: null,
      approved_by_name: null,
      receipt_pdf_base64: "cGRmLWRhdGE=",
      created_at: new Date().toISOString(),
    });

    promptCorporateReasonMock.mockReturnValue("Motivo corporativo");

    render(<Purchases />);

    await waitFor(() => expect(getPurchaseSuggestionsMock).toHaveBeenCalled());

    const storeSelect = await screen.findByLabelText("Sucursal");
    fireEvent.change(storeSelect, { target: { value: "1" } });

    await waitFor(() => expect(listPurchaseOrdersMock).toHaveBeenCalledWith("token", 1, 100));

    const orderSelect = await screen.findByLabelText("Orden de compra");
    fireEvent.change(orderSelect, { target: { value: "77" } });

    const deviceSelect = await screen.findByLabelText("Dispositivo");
    fireEvent.change(deviceSelect, { target: { value: "2001" } });

    const quantityInput = await screen.findByLabelText(/Cantidad a devolver/i);
    fireEvent.change(quantityInput, { target: { value: "2" } });

    const reasonInput = screen.getByPlaceholderText("Describe el motivo técnico");
    fireEvent.change(reasonInput, { target: { value: "Proveedor defectuoso" } });

    const submitButton = screen.getByRole("button", { name: /Registrar devolución/i });
    fireEvent.click(submitButton);

    await waitFor(() => expect(registerPurchaseReturnMock).toHaveBeenCalled());

    expect(registerPurchaseReturnMock).toHaveBeenCalledWith(
      "token",
      77,
      {
        device_id: 2001,
        quantity: 2,
        reason: "Proveedor defectuoso",
        disposition: "defectuoso",
        category: "defecto",
      },
      "Motivo corporativo",
    );

    expect(promptCorporateReasonMock).toHaveBeenCalled();
    expect(screen.getByText(/Nota de crédito por .*180\.00/)).toBeInTheDocument();
    const receiptLink = await screen.findByRole("link", {
      name: /Descargar comprobante generado/i,
    });
    expect(URL.createObjectURL).toHaveBeenCalled();
    expect(receiptLink).toBeInTheDocument();
    expect(receiptLink).toHaveAttribute("download", "devolucion-77-900.pdf");
    expect(receiptLink).toHaveAttribute("href", "blob:url");
  });
});
