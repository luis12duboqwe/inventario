import { Suspense, act } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import OperationsPage from "./OperationsPage";

const customersSpy = vi.fn(() => <div data-testid="customers-panel" />);
const suppliersSpy = vi.fn(() => <div data-testid="suppliers-panel" />);
const posSpy = vi.fn(() => <div data-testid="pos-panel" />);
const purchasesSpy = vi.fn(() => <div data-testid="purchases-panel" />);
const salesSpy = vi.fn(() => <div data-testid="sales-panel" />);
const returnsSpy = vi.fn(() => <div data-testid="returns-panel" />);
const transfersSpy = vi.fn(() => <div data-testid="transfers-panel" />);
const internalSpy = vi.fn(() => <div data-testid="internal-panel" />);
const historySpy = vi.fn(() => <div data-testid="history-panel" />);

vi.mock("../components/Customers", () => ({ default: customersSpy }));
vi.mock("../components/Suppliers", () => ({ default: suppliersSpy }));
vi.mock("../components/POS/POSDashboard", () => ({ default: posSpy }));
vi.mock("../components/Purchases", () => ({ default: purchasesSpy }));
vi.mock("../components/Sales", () => ({ default: salesSpy }));
vi.mock("../components/Returns", () => ({ default: returnsSpy }));
vi.mock("../components/TransferOrders", () => ({ default: transfersSpy }));
vi.mock("../components/InternalMovementsPanel", () => ({ default: internalSpy }));
vi.mock("../components/OperationsHistoryPanel", () => ({ default: historySpy }));

vi.mock("../hooks/useOperationsModule", () => ({
  useOperationsModule: () => ({
    token: "token-demo",
    stores: [
      { id: 1, name: "Central", status: "activa", code: "SUC-001", timezone: "America/Mexico_City" },
    ],
    selectedStoreId: 1,
    enablePurchasesSales: true,
    enableTransfers: true,
    refreshInventoryAfterTransfer: vi.fn(),
  }),
}));

describe("OperationsPage carga diferida", () => {
  it("monta paneles pesados sólo al expandirlos", async () => {
    const user = userEvent.setup();

    await act(async () => {
      render(
        <Suspense fallback={<div data-testid="fallback" />}>
          <OperationsPage />
        </Suspense>,
      );
    });

    await screen.findByTestId("customers-panel");
    expect(customersSpy).toHaveBeenCalledOnce();
    expect(suppliersSpy).toHaveBeenCalledOnce();
    expect(posSpy).toHaveBeenCalledOnce();
    expect(purchasesSpy).toHaveBeenCalledOnce();
    expect(salesSpy).toHaveBeenCalledOnce();
    expect(returnsSpy).toHaveBeenCalledOnce();
    expect(internalSpy).not.toHaveBeenCalled();
    expect(transfersSpy).not.toHaveBeenCalled();
    expect(historySpy).not.toHaveBeenCalled();

    const internalButton = screen.getByRole("button", { name: /movimientos internos/i });
    await user.click(internalButton);
    await screen.findByTestId("internal-panel");
    expect(internalSpy).toHaveBeenCalledOnce();

    const transfersButton = screen.getByRole("button", { name: /transferencias entre tiendas/i });
    await user.click(transfersButton);
    await screen.findByTestId("transfers-panel");
    expect(transfersSpy).toHaveBeenCalledOnce();

    const historyButton = screen.getByRole("button", { name: /historial de operaciones/i });
    await user.click(historyButton);
    await screen.findByTestId("history-panel");
    expect(historySpy).toHaveBeenCalledOnce();
  });
});
