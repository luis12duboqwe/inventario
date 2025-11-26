import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Store } from "../../../../api";

const listPurchaseOrdersMock = vi.hoisted(() => vi.fn());
const listSalesMock = vi.hoisted(() => vi.fn());
const registerPurchaseReturnMock = vi.hoisted(() => vi.fn());
const registerSaleReturnMock = vi.hoisted(() => vi.fn());
const listReturnsMock = vi.hoisted(() => vi.fn());
const searchSalesHistoryMock = vi.hoisted(() => vi.fn());

const apiModuleId = vi.hoisted(
  () => new URL("../../../../api.ts", import.meta.url).pathname,
);

vi.mock("../../../../api", () => ({
  __esModule: true,
  listPurchaseOrders: listPurchaseOrdersMock,
  listSales: listSalesMock,
  registerPurchaseReturn: registerPurchaseReturnMock,
  registerSaleReturn: registerSaleReturnMock,
  listReturns: listReturnsMock,
  searchSalesHistory: searchSalesHistoryMock,
}));

vi.mock(apiModuleId, () => ({
  __esModule: true,
  listPurchaseOrders: listPurchaseOrdersMock,
  listSales: listSalesMock,
  registerPurchaseReturn: registerPurchaseReturnMock,
  registerSaleReturn: registerSaleReturnMock,
  listReturns: listReturnsMock,
  searchSalesHistory: searchSalesHistoryMock,
}));

import Returns from "../Returns";

describe("Returns", () => {
  beforeEach(() => {
    listPurchaseOrdersMock.mockReset();
    listSalesMock.mockReset();
    registerPurchaseReturnMock.mockReset();
    registerSaleReturnMock.mockReset();
    listReturnsMock.mockReset();
    searchSalesHistoryMock.mockReset();

    listPurchaseOrdersMock.mockResolvedValue([]);
    listSalesMock.mockResolvedValue([]);
    listReturnsMock.mockResolvedValue({
      items: [
        {
          id: 1,
          type: "sale",
          reference_id: 10,
          reference_label: "Venta #10",
          store_id: 1,
          store_name: "Sucursal Norte",
          device_id: 5,
          device_name: "Lectura",
          quantity: 1,
          reason: "Cambio del cliente - color incorrecto",
          reason_category: "cliente",
          disposition: "vendible",
          warehouse_id: null,
          warehouse_name: null,
          processed_by_id: 7,
          processed_by_name: "Operador Uno",
          approved_by_id: 9,
          approved_by_name: "Supervisora Central",
          partner_name: "María Pérez",
          occurred_at: new Date("2025-02-01T12:00:00Z").toISOString(),
          refund_amount: 120,
          payment_method: "EFECTIVO",
        },
        {
          id: 2,
          type: "purchase",
          reference_id: 22,
          reference_label: "Compra #22",
          store_id: 1,
          store_name: "Sucursal Norte",
          device_id: 9,
          device_name: "Terminal",
          quantity: 2,
          reason: "Falla de calidad - sin carga",
          reason_category: "defecto",
          disposition: "defectuoso",
          warehouse_id: 4,
          warehouse_name: "Almacén QA",
          processed_by_id: 7,
          processed_by_name: "Operador Uno",
          approved_by_id: null,
          approved_by_name: null,
          partner_name: "Proveedor Central",
          occurred_at: new Date("2025-02-01T10:00:00Z").toISOString(),
        },
      ],
      totals: {
        total: 2,
        sales: 1,
        purchases: 1,
        refunds_by_method: { EFECTIVO: 120 },
        refund_total_amount: 120,
        categories: { cliente: 1, defecto: 1 },
      },
    });
  });

  it("muestra el historial de devoluciones con motivos y totales", async () => {
    const stores: Store[] = [
      {
        id: 1,
        name: "Sucursal Norte",
        status: "ACTIVA",
        code: "NOR",
        timezone: "America/Mexico_City",
        inventory_value: 0,
        created_at: "2025-02-01T00:00:00Z",
        location: "MX",
        phone: null,
        manager: null,
      },
    ];

    render(
      <Returns token="test-token" stores={stores} defaultStoreId={1} />,
    );

    const [purchaseReasonInput, saleReasonInput] =
      screen.getAllByLabelText("Motivo corporativo");

    expect(purchaseReasonInput).toHaveValue("Falla de calidad");
    expect(saleReasonInput).toHaveValue("Cambio del cliente");

    await waitFor(() => {
      expect(listReturnsMock).toHaveBeenCalledWith("test-token", {
        limit: 25,
        storeId: 1,
      });
    });

    expect(
      await screen.findByText("Historial de devoluciones"),
    ).toBeInTheDocument();
    expect(screen.getByText("Total: 2")).toBeInTheDocument();
    expect(screen.getByText("Clientes: 1")).toBeInTheDocument();
    expect(screen.getByText("Proveedores: 1")).toBeInTheDocument();
    expect(screen.getByText("Reembolsos: $120.00")).toBeInTheDocument();
    expect(screen.getByText("EFECTIVO: $120.00")).toBeInTheDocument();
    expect(screen.getByText("Cambio del cliente: 1")).toBeInTheDocument();
    expect(screen.getByText("Falla de calidad: 1")).toBeInTheDocument();
    expect(screen.getByText("Cambio del cliente - color incorrecto")).toBeInTheDocument();
    expect(screen.getByText("Falla de calidad - sin carga")).toBeInTheDocument();
    expect(screen.getByText("Cambio del cliente")).toBeInTheDocument();
    expect(screen.getByText("Falla de calidad")).toBeInTheDocument();
    expect(screen.getByText("Vendible")).toBeInTheDocument();
    expect(screen.getByText("Almacén QA")).toBeInTheDocument();
    expect(screen.getAllByText("Cliente")).not.toHaveLength(0);
  });

  it("permite refrescar el historial manualmente", async () => {
    const stores: Store[] = [
      {
        id: 3,
        name: "Sucursal Centro",
        status: "ACTIVA",
        code: "CEN",
        timezone: "America/Mexico_City",
        inventory_value: 0,
        created_at: "2025-02-01T00:00:00Z",
        location: "MX",
        phone: null,
        manager: null,
      },
    ];

    render(
      <Returns token="token-refresh" stores={stores} defaultStoreId={3} />,
    );

    const refreshButton = await screen.findByRole("button", {
      name: "Actualizar",
    });

    const user = userEvent.setup();
    await user.click(refreshButton);

    await waitFor(() => {
      expect(listReturnsMock).toHaveBeenLastCalledWith("token-refresh", {
        limit: 25,
        storeId: 3,
      });
    });
  });
});
