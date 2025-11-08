import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthzProvider } from "../../../../auth/useAuthz";
import POSPage from "../POSPage";
import type { ProductSearchParams, Totals } from "../../../../services/sales";
import { SalesPOS, SalesProducts } from "../../../../services/sales";

vi.mock("../../../../services/audit", () => ({
  logUI: vi.fn(),
}));

vi.mock("@/lib/print", () => ({
  openPrintable: vi.fn(),
}));

describe("POSPage - entrada rápida", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("agrega el producto al carrito al recibir un código de escáner", async () => {
    const totals: Totals = { sub: 0, disc: 0, tax: 0, grand: 0 };
    vi.spyOn(SalesPOS, "priceDraft").mockResolvedValue(totals);
    vi.spyOn(SalesPOS, "checkout").mockResolvedValue({
      saleId: "sale-1",
      number: "F0001",
      date: new Date().toISOString(),
      totals,
    });
    vi.spyOn(SalesPOS, "holdSale").mockResolvedValue({ holdId: "hold-1" });
    vi.spyOn(SalesPOS, "resumeHold").mockResolvedValue({ lines: [], payments: [] });

    const searchMock = vi
      .spyOn(SalesProducts, "searchProducts")
      .mockImplementation(async (params: ProductSearchParams) => {
        if ((params.q ?? "").toUpperCase() === "SKU123") {
          return {
            items: [
              { id: "prod-1", name: "Producto Escaneado", price: 150, sku: "SKU123" },
            ],
            total: 1,
            page: params.page ?? 1,
            pageSize: params.pageSize ?? 1,
          };
        }
        return {
          items: [],
          total: 0,
          page: params.page ?? 1,
          pageSize: params.pageSize ?? 24,
        };
      });

    render(
      <AuthzProvider user={{ id: "user-1", name: "Cajero", role: "ADMIN" }}>
        <POSPage />
      </AuthzProvider>,
    );

    await waitFor(() => expect(searchMock).toHaveBeenCalled());

    fireEvent.keyDown(window, { key: "S" });
    fireEvent.keyDown(window, { key: "K" });
    fireEvent.keyDown(window, { key: "U" });
    fireEvent.keyDown(window, { key: "1" });
    fireEvent.keyDown(window, { key: "2" });
    fireEvent.keyDown(window, { key: "3" });
    fireEvent.keyDown(window, { key: "Enter" });

    await waitFor(() => {
      expect(searchMock).toHaveBeenCalledWith(
        expect.objectContaining({ q: "SKU123", sku: "SKU123", imei: "SKU123" }),
      );
      const productLabels = screen.getAllByText("Producto Escaneado");
      expect(productLabels.length).toBeGreaterThan(0);
    });

    await waitFor(() => {
      const status = screen.getByRole("status");
      expect(status.textContent ?? "").toMatch(/Producto Escaneado|Código SKU123/i);
    });
  });

  it("ignora el lector desactivado pero permite captura manual forzada", async () => {
    const totals: Totals = { sub: 0, disc: 0, tax: 0, grand: 0 };
    vi.spyOn(SalesPOS, "priceDraft").mockResolvedValue(totals);
    vi.spyOn(SalesPOS, "checkout").mockResolvedValue({
      saleId: "sale-1",
      number: "F0001",
      date: new Date().toISOString(),
      totals,
    });
    vi.spyOn(SalesPOS, "holdSale").mockResolvedValue({ holdId: "hold-1" });
    vi.spyOn(SalesPOS, "resumeHold").mockResolvedValue({ lines: [], payments: [] });

    const searchMock = vi
      .spyOn(SalesProducts, "searchProducts")
      .mockImplementation(async (params: ProductSearchParams) => {
        if ((params.q ?? "").toUpperCase() === "SKU321") {
          return {
            items: [
              { id: "prod-2", name: "Producto Manual", price: 99, sku: "SKU321" },
            ],
            total: 1,
            page: params.page ?? 1,
            pageSize: params.pageSize ?? 1,
          };
        }
        return {
          items: [],
          total: 0,
          page: params.page ?? 1,
          pageSize: params.pageSize ?? 24,
        };
      });

    render(
      <AuthzProvider user={{ id: "user-1", name: "Cajero", role: "ADMIN" }}>
        <POSPage />
      </AuthzProvider>,
    );

    await waitFor(() => expect(searchMock).toHaveBeenCalled());
    expect(searchMock).toHaveBeenCalledTimes(1);

    const toggle = screen.getByLabelText("Escuchar escáner global");
    fireEvent.click(toggle);

    fireEvent.keyDown(window, { key: "S" });
    fireEvent.keyDown(window, { key: "K" });
    fireEvent.keyDown(window, { key: "U" });
    fireEvent.keyDown(window, { key: "9" });
    fireEvent.keyDown(window, { key: "9" });
    fireEvent.keyDown(window, { key: "9" });
    fireEvent.keyDown(window, { key: "Enter" });

    await waitFor(() => expect(searchMock).toHaveBeenCalledTimes(1));

    const manualInput = screen.getByLabelText("Código manual");
    fireEvent.change(manualInput, { target: { value: "SKU321" } });
    fireEvent.submit(manualInput.closest("form") as HTMLFormElement);

    await waitFor(() => {
      expect(searchMock).toHaveBeenCalledWith(
        expect.objectContaining({ q: "SKU321", sku: "SKU321", imei: "SKU321" }),
      );
      const productLabels = screen.getAllByText("Producto Manual");
      expect(productLabels.length).toBeGreaterThan(0);
    });
  });
});
