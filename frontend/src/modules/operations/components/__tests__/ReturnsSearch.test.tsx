import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { SaleHistorySearchResponse } from "../../../../api";

const searchSalesHistoryMock = vi.hoisted(() => vi.fn());

const apiModuleId = vi.hoisted(
  () => new URL("../../../../api.ts", import.meta.url).pathname,
);

vi.mock("../../../../api", () => ({
  __esModule: true,
  searchSalesHistory: searchSalesHistoryMock,
}));

vi.mock(apiModuleId, () => ({
  __esModule: true,
  searchSalesHistory: searchSalesHistoryMock,
}));

import ReturnsSearch from "../ReturnsSearch";

describe("ReturnsSearch", () => {
  beforeEach(() => {
    searchSalesHistoryMock.mockReset();
    searchSalesHistoryMock.mockResolvedValue({
      by_ticket: [],
      by_qr: [],
      by_customer: [],
      by_date: [],
    } satisfies SaleHistorySearchResponse);
  });

  it("requiere criterios antes de buscar", async () => {
    render(<ReturnsSearch token="token-test" />);

    const button = screen.getByRole("button", { name: "Buscar historial" });
    const user = userEvent.setup();
    await user.click(button);

    expect(
      await screen.findByText("Ingresa al menos un criterio para realizar la búsqueda."),
    ).toBeInTheDocument();
    expect(searchSalesHistoryMock).not.toHaveBeenCalled();
  });

  it("envía filtros combinados y muestra segmentos", async () => {
    const saleDate = new Date("2025-02-01T13:45:00Z").toISOString();
    searchSalesHistoryMock.mockResolvedValue({
      by_ticket: [
        {
          id: 101,
          store_id: 5,
          payment_method: "EFECTIVO",
          discount_percent: 0,
          subtotal_amount: 100,
          tax_amount: 16,
          total_amount: 116,
          created_at: saleDate,
          items: [],
          returns: [],
          store: { id: 5, name: "Sucursal Centro" },
          customer_name: "Cliente Preferente",
        },
      ],
      by_qr: [],
      by_customer: [],
      by_date: [
        {
          id: 202,
          store_id: 7,
          payment_method: "TARJETA",
          discount_percent: 5,
          subtotal_amount: 200,
          tax_amount: 32,
          total_amount: 232,
          created_at: saleDate,
          items: [],
          returns: [],
          store: { id: 7, name: "Sucursal Norte" },
          customer_name: "Ana López",
        },
      ],
      by_customer: [],
    } satisfies SaleHistorySearchResponse);

    render(<ReturnsSearch token="token-busqueda" />);

    const ticketInput = screen.getByLabelText("Ticket o folio");
    const dateInput = screen.getByLabelText("Fecha de operación");
    const customerInput = screen.getByLabelText("Cliente");
    const qrInput = screen.getByLabelText("Escaneo de recibo (QR)");

    const user = userEvent.setup();
    await user.type(ticketInput, " SM-000101 ");
    await user.type(dateInput, "2025-02-01");
    await user.type(customerInput, "  Ana   ");
    await user.type(qrInput, "{\"sale_id\":101}");
    await user.click(screen.getByRole("button", { name: "Buscar historial" }));

    await waitFor(() => {
      expect(searchSalesHistoryMock).toHaveBeenCalledWith("token-busqueda", {
        ticket: "SM-000101",
        date: "2025-02-01",
        customer: "Ana",
        qr: "{\"sale_id\":101}",
        limit: 25,
      });
    });

    expect(await screen.findByText("Coincidencias por ticket")).toBeInTheDocument();
    expect(screen.getByText("Venta #101")).toBeInTheDocument();
    expect(screen.getByText("Sucursal Centro")).toBeInTheDocument();
    expect(screen.getByText("Coincidencias por fecha")).toBeInTheDocument();
    expect(screen.getByText("Venta #202")).toBeInTheDocument();
  });
});
