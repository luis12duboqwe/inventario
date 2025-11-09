import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Sale } from "../../../../api";

const registerSaleReturnMock = vi.hoisted(() => vi.fn());
const downloadPosReceiptMock = vi.hoisted(() => vi.fn());

const apiModuleId = vi.hoisted(
  () => new URL("../../../../api.ts", import.meta.url).pathname,
);

vi.mock("../../../../api", () => ({
  __esModule: true,
  registerSaleReturn: registerSaleReturnMock,
  downloadPosReceipt: downloadPosReceiptMock,
}));

vi.mock(apiModuleId, () => ({
  __esModule: true,
  registerSaleReturn: registerSaleReturnMock,
  downloadPosReceipt: downloadPosReceiptMock,
}));

import ReceiptPreview from "../ReceiptPreview";

describe("ReceiptPreview", () => {
  afterEach(() => {
    registerSaleReturnMock.mockReset();
    downloadPosReceiptMock.mockReset();
    vi.restoreAllMocks();
  });

  it("confirma el reembolso con el medio de pago original y muestra el mensaje guía", async () => {
    registerSaleReturnMock.mockResolvedValue([]);

    const sale: Sale = {
      id: 101,
      store_id: 1,
      customer_id: null,
      customer_name: "Cliente POS",
      payment_method: "EFECTIVO",
      discount_percent: 0,
      subtotal_amount: 240,
      tax_amount: 0,
      total_amount: 240,
      notes: null,
      created_at: new Date("2025-02-01T12:00:00Z").toISOString(),
      performed_by_id: 3,
      cash_session_id: null,
      customer: null,
      cash_session: null,
      items: [
        {
          id: 501,
          sale_id: 101,
          device_id: 5,
          quantity: 2,
          unit_price: 120,
          discount_amount: 0,
          total_line: 240,
        },
      ],
      returns: [],
      payment_breakdown: undefined,
      store: null,
      performed_by: null,
    };

    const promptSpy = vi
      .spyOn(window, "prompt")
      .mockImplementationOnce(() => "5")
      .mockImplementationOnce(() => "1")
      .mockImplementationOnce(() => "Motivo cliente")
      .mockImplementationOnce(() => "Motivo corporativo");
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<ReceiptPreview token="test-token" sale={sale} />);

    const button = screen.getByRole("button", { name: "Registrar devolución" });
    const user = userEvent.setup();
    await user.click(button);

    expect(promptSpy).toHaveBeenCalledTimes(4);
    expect(confirmSpy).toHaveBeenCalledWith(
      expect.stringContaining("EFECTIVO: $120.00"),
    );
    expect(registerSaleReturnMock).toHaveBeenCalledWith(
      "test-token",
      {
        sale_id: 101,
        items: [
          {
            device_id: 5,
            quantity: 1,
            reason: "Motivo cliente",
          },
        ],
      },
      "Motivo corporativo",
    );

    expect(
      await screen.findByText(
        "Devolución registrada. Reintegra EFECTIVO: $120.00 y actualiza la caja correspondiente.",
      ),
    ).toBeInTheDocument();
  });
});
