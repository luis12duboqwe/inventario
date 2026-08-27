import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, beforeEach, vi } from "vitest";

import OperationsPOS from "../../../pages/OperationsPOS";
import { getDevices } from "@api/inventory";

const moduleState = {
  token: "token-123",
  stores: [{ id: 1, name: "Sucursal Centro" }],
  selectedStoreId: 1,
  enablePurchasesSales: true,
  enableTransfers: true,
};

vi.mock("../../../hooks/useOperationsModule", () => ({
  useOperationsModule: () => moduleState,
}));

vi.mock("../../../../dashboard/context/DashboardContext", () => ({
  useDashboard: () => ({
    token: "token-123",
    pushToast: vi.fn(),
  }),
}));

vi.mock("@api/inventory", () => ({
  getDevices: vi.fn(async () => [
    {
      id: 10,
      sku: "IPH15-128-BLK",
      name: "iPhone 15 128GB Negro",
      quantity: 1,
      store_id: 1,
      unit_price: 18000,
      precio_venta: 18500,
      inventory_value: 18000,
      completo: true,
      imei: "356789012345678",
      serial: "SN-IP15-001",
    },
  ]),
}));

vi.mock("@api/pos", () => ({
  closePosSession: vi.fn(async () => ({
    session_id: 1,
    branch_id: 1,
    status: "CERRADO",
    opened_at: new Date().toISOString(),
    payment_breakdown: {},
  })),
  getLastPosSession: vi.fn(async () => ({
    session_id: 1,
    branch_id: 1,
    status: "ABIERTO",
    opened_at: new Date().toISOString(),
    payment_breakdown: {},
  })),
  getPosSaleDetail: vi.fn(async () => ({
    sale: {
      id: 1,
      store_id: 1,
      customer_id: null,
      customer_name: null,
      payment_method: "EFECTIVO",
      discount_percent: 0,
      subtotal_amount: 0,
      tax_amount: 0,
      total_amount: 0,
      notes: null,
      created_at: new Date().toISOString(),
      performed_by_id: null,
      cash_session_id: null,
      items: [],
      returns: [],
    },
    receipt_url: "/pos/receipt/1",
  })),
  listPosTaxes: vi.fn(async () => [{ code: "IVA", name: "IVA", rate: 16 }]),
  openPosSession: vi.fn(async () => ({
    session_id: 1,
    branch_id: 1,
    status: "ABIERTO",
    opened_at: new Date().toISOString(),
    payment_breakdown: {},
  })),
  registerPosReturn: vi.fn(async () => ({ sale_id: 1, return_ids: [1] })),
  submitPosSaleOperation: vi.fn(async () => ({
    status: "registered",
    sale: {
      id: 1,
      store_id: 1,
      customer_id: null,
      customer_name: null,
      payment_method: "EFECTIVO",
      discount_percent: 0,
      subtotal_amount: 0,
      tax_amount: 0,
      total_amount: 0,
      notes: null,
      created_at: new Date().toISOString(),
      performed_by_id: null,
      cash_session_id: null,
      items: [],
      returns: [],
    },
    receipt_url: "/pos/receipt/1",
  })),
}));

const getDevicesMock = vi.mocked(getDevices);

// [PACK34-UI]
describe("OperationsPOS", () => {
  beforeEach(() => {
    moduleState.enablePurchasesSales = true;
    getDevicesMock.mockClear();
  });

  it("muestra la estructura principal del POS", async () => {
    render(<OperationsPOS />);

    expect(await screen.findByText(/POS \/ Caja/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/Totales/)).toBeInTheDocument());
  });

  it("agrega al carrito un equipo escaneado desde el inventario real de la sucursal", async () => {
    const user = userEvent.setup();
    render(<OperationsPOS />);

    const input = await screen.findByRole("textbox", { name: "Código manual" });
    await user.type(input, "356789012345678");
    await user.click(screen.getByRole("button", { name: "Aplicar" }));

    await waitFor(() =>
      expect(getDevicesMock).toHaveBeenCalledWith("token-123", 1, {
        search: "356789012345678",
        limit: 20,
      }),
    );
    expect(await screen.findByText("iPhone 15 128GB Negro")).toBeInTheDocument();
  });

  it("informa cuando el flag de ventas y compras está desactivado", async () => {
    moduleState.enablePurchasesSales = false;

    render(<OperationsPOS />);

    expect(await screen.findByText(/Activa el flag corporativo/i)).toBeInTheDocument();
    expect(screen.queryByText(/Totales/)).not.toBeInTheDocument();
  });
});
