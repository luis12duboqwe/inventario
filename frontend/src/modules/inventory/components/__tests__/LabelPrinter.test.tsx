import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const downloadDeviceLabelPdfMock = vi.hoisted(() => vi.fn());
const useAuthMock = vi.hoisted(() => vi.fn());

vi.mock("../../../../api", () => ({
  __esModule: true,
  downloadDeviceLabelPdf: downloadDeviceLabelPdfMock,
}));

vi.mock("../../../auth/useAuth", () => ({
  __esModule: true,
  useAuth: () => useAuthMock(),
}));

import LabelGenerator from "../LabelGenerator";

describe("LabelGenerator", () => {
  const renderComponent = () =>
    render(
      <LabelGenerator
        open
        storeId={5}
        storeName="Sucursal Centro"
        deviceId="101"
        deviceName="Equipo demo"
        sku="SKU-101"
        onClose={vi.fn()}
      />,
    );

  beforeEach(() => {
    downloadDeviceLabelPdfMock.mockReset();
    useAuthMock.mockReturnValue({ accessToken: "token-123" });
  });

  it("genera el PDF y muestra vista previa", async () => {
    const blob = new Blob(["demo"], { type: "application/pdf" });
    downloadDeviceLabelPdfMock.mockResolvedValueOnce({ blob, filename: "etiqueta-demo.pdf" });

    renderComponent();

    const reasonInput = screen.getByLabelText(/Motivo corporativo/i);
    const user = userEvent.setup();
    await user.clear(reasonInput);
    await user.type(reasonInput, "Motivo válido");

    await user.click(screen.getByRole("button", { name: /Generar etiqueta/i }));

    await waitFor(() => {
      expect(downloadDeviceLabelPdfMock).toHaveBeenCalledWith("token-123", 5, 101, "Motivo válido");
    });

    expect(await screen.findByRole("link", { name: /etiqueta-demo.pdf/i })).toBeInTheDocument();
  });

  it("muestra error cuando el motivo corporativo es corto", async () => {
    renderComponent();

    const reasonInput = screen.getByLabelText(/Motivo corporativo/i);
    const user = userEvent.setup();
    await user.clear(reasonInput);
    await user.type(reasonInput, "abc");

    await user.click(screen.getByRole("button", { name: /Generar etiqueta/i }));

    expect(await screen.findByText(/al menos 5 caracteres/i)).toBeInTheDocument();
    expect(downloadDeviceLabelPdfMock).not.toHaveBeenCalled();
  });

  it("restablece el estado al cerrar", async () => {
    renderComponent();

    const reasonInput = screen.getByLabelText(/Motivo corporativo/i);
    const user = userEvent.setup();
    await user.clear(reasonInput);
    await user.type(reasonInput, "Motivo válido");

    await user.click(screen.getByRole("button", { name: /Cancelar/i }));

    expect(reasonInput).toHaveValue("Impresión de etiqueta");
  });
});
