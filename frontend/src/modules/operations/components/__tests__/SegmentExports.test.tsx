import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { CustomerSegmentDefinition } from "../../../../types/customers";
import CustomersSegmentExports from "../customers/SegmentExports";

describe("CustomersSegmentExports", () => {
  const segments: CustomerSegmentDefinition[] = [
    {
      key: "alto_valor",
      label: "Clientes de alto valor",
      description: "Campañas para Mailchimp",
      channel: "Mailchimp",
    },
    {
      key: "recuperacion",
      label: "Campaña de recuperación",
      description: "Recordatorios SMS",
      channel: "SMS",
    },
  ];

  it("renderiza botones e invoca la exportación", async () => {
    const onExport = vi.fn();
    render(
      <CustomersSegmentExports
        segments={segments}
        exportingKey={null}
        onExport={onExport}
      />,
    );

    const user = userEvent.setup();
    const button = screen.getByRole("button", { name: /Clientes de alto valor/i });
    await user.click(button);

    expect(onExport).toHaveBeenCalledWith(segments[0]);
    expect(screen.getByText("Campaña de recuperación")).toBeInTheDocument();
  });

  it("muestra estado de carga cuando se está exportando", () => {
    render(
      <CustomersSegmentExports
        segments={segments}
        exportingKey="recuperacion"
        onExport={vi.fn()}
      />,
    );

    const busyButton = screen.getByRole("button", { name: /Campaña de recuperación/i });
    expect(busyButton).toBeDisabled();
    expect(screen.getByText(/Generando…/)).toBeInTheDocument();
  });
});
