import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import CashDrawer from "../CashDrawer";
import type { PosSessionSummary } from "../../../../services/api/pos";

const baseSession: PosSessionSummary = {
  session_id: 7,
  branch_id: 1,
  status: "ABIERTO",
  opened_at: new Date("2024-01-01T10:00:00Z").toISOString(),
  closing_at: null,
  opening_amount: 500,
  closing_amount: null,
  expected_amount: 500,
  difference_amount: 0,
  payment_breakdown: { EFECTIVO: 500 },
};

describe("CashDrawer", () => {
  it("muestra el encabezado, los montos y permite refrescar la información", async () => {
    const user = userEvent.setup();
    const handleOpen = vi.fn().mockResolvedValue(undefined);
    const handleClose = vi.fn().mockResolvedValue(undefined);
    const handleRefresh = vi.fn();

    render(
      <CashDrawer
        stores={[{ id: 1, name: "Matriz" }]}
        selectedStoreId={1}
        onStoreChange={vi.fn()}
        session={baseSession}
        onOpenSession={handleOpen}
        onCloseSession={handleClose}
        refreshing={false}
        onRefresh={handleRefresh}
      />,
    );

    expect(screen.getByRole("heading", { level: 3, name: /Caja/i })).toBeInTheDocument();
    expect(screen.getAllByText("$500.00")).not.toHaveLength(0);

    await user.click(screen.getByRole("button", { name: /Actualizar/i }));
    expect(handleRefresh).toHaveBeenCalledTimes(1);
  });
});
