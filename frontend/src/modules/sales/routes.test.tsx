import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

vi.mock("../operations/pages/OperationsPOS", () => ({
  default: () => <div data-testid="canonical-operations-pos">POS canónico</div>,
}));

vi.mock("./pages/POSPage", () => ({
  default: () => <div data-testid="legacy-sales-pos">POS legacy</div>,
}));

import SalesRoutes from "./routes";

describe("SalesRoutes", () => {
  it("monta OperationsPOS y no el POS legacy en /sales/pos", async () => {
    render(
      <MemoryRouter initialEntries={["/pos"]}>
        <SalesRoutes />
      </MemoryRouter>,
    );

    expect(await screen.findByTestId("canonical-operations-pos")).toBeInTheDocument();
    expect(screen.queryByTestId("legacy-sales-pos")).not.toBeInTheDocument();
  });
});
