import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

vi.mock("../operations/pages/OperationsPOS", () => ({
  default: () => <div data-testid="canonical-operations-pos">POS canónico</div>,
}));

import SalesRoutes from "./routes";

describe("SalesRoutes", () => {
  it("monta OperationsPOS como implementación canónica en /sales/pos", async () => {
    render(
      <MemoryRouter initialEntries={["/pos"]}>
        <SalesRoutes />
      </MemoryRouter>,
    );

    expect(await screen.findByTestId("canonical-operations-pos")).toBeInTheDocument();
  });
});
