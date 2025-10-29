import { Suspense, act } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter, Navigate, Route, Routes } from "react-router-dom";

import OperationsPage from "./OperationsPage";

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

describe("OperationsPage navegación", () => {
  it("muestra paneles al navegar entre secciones", async () => {
    const user = userEvent.setup();

    await act(async () => {
      render(
        <MemoryRouter initialEntries={["/dashboard/operations"]}>
          <Routes>
            <Route
              path="/dashboard/operations/*"
              element={
                <Suspense fallback={<div data-testid="fallback" />}>
                  <OperationsPage />
                </Suspense>
              }
            >
              <Route index element={<Navigate to="ventas/caja" replace />} />
              <Route path="ventas">
                <Route index element={<Navigate to="caja" replace />} />
                <Route path="caja" element={<div data-testid="pos-panel" />} />
                <Route path="clientes" element={<div data-testid="customers-panel" />} />
                <Route path="facturacion" element={<div data-testid="sales-panel" />} />
              </Route>
              <Route path="compras">
                <Route index element={<Navigate to="ordenes" replace />} />
                <Route path="ordenes" element={<div data-testid="purchases-panel" />} />
              </Route>
              <Route path="movimientos">
                <Route index element={<Navigate to="internos" replace />} />
                <Route path="internos" element={<div data-testid="internal-panel" />} />
                <Route path="transferencias" element={<div data-testid="transfers-panel" />} />
              </Route>
            </Route>
          </Routes>
        </MemoryRouter>,
      );
    });

    expect(await screen.findByTestId("pos-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("customers-panel")).not.toBeInTheDocument();
    expect(screen.queryByTestId("internal-panel")).not.toBeInTheDocument();
    expect(screen.queryByTestId("transfers-panel")).not.toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: /clientes/i }));
    expect(await screen.findByTestId("customers-panel")).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: /movimientos internos/i }));
    expect(await screen.findByTestId("internal-panel")).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: /transferencias/i }));
    expect(await screen.findByTestId("transfers-panel")).toBeInTheDocument();
  });
});
