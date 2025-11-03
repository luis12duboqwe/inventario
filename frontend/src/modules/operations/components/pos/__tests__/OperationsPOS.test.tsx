import { render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import OperationsPOS from "../../../pages/OperationsPOS";

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

vi.mock("../../../../../services/api/pos", () => ({
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

// [PACK34-UI]
describe("OperationsPOS", () => {
  beforeEach(() => {
    moduleState.enablePurchasesSales = true;
  });

  it("muestra la estructura principal del POS", async () => {
    render(<OperationsPOS />);

    expect(await screen.findByText(/POS \/ Caja/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/Totales/)).toBeInTheDocument());
  });

  it("informa cuando el flag de ventas y compras está desactivado", () => {
    moduleState.enablePurchasesSales = false;

    render(<OperationsPOS />);

    expect(screen.getByText(/Activa el flag corporativo/i)).toBeInTheDocument();
    expect(screen.queryByText(/Totales/)).not.toBeInTheDocument();
  });
});

