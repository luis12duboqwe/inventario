import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const requestDeviceLabelMock = vi.hoisted(() => vi.fn());
const triggerDeviceLabelPrintMock = vi.hoisted(() => vi.fn());
const useAuthMock = vi.hoisted(() => vi.fn());

vi.mock("@api/inventory", () => ({
  __esModule: true,
  requestDeviceLabel: requestDeviceLabelMock,
  triggerDeviceLabelPrint: triggerDeviceLabelPrintMock,
}));

vi.mock("../../../auth/useAuth", () => ({
  __esModule: true,
  useAuth: () => useAuthMock(),
}));

import LabelPrinter from "../LabelPrinter";

describe("LabelPrinter", () => {
  const renderComponent = () =>
    render(
      <LabelPrinter
        open
        fallbackStoreId={5}
        fallbackStoreName="Sucursal Centro"
        fallbackDeviceId="101"
        fallbackDeviceName="Equipo demo"
        fallbackSku="SKU-101"
        onClose={vi.fn()}
      />,
    );

  beforeEach(() => {
    requestDeviceLabelMock.mockReset();
    triggerDeviceLabelPrintMock.mockReset();
    useAuthMock.mockReturnValue({ accessToken: "token-123" });
  });

  it("genera el PDF y muestra vista previa", async () => {
    const blob = new Blob(["demo"], { type: "application/pdf" });
    requestDeviceLabelMock.mockResolvedValueOnce({ blob, filename: "etiqueta-demo.pdf" });

    renderComponent();

    const reasonInput = screen.getByLabelText(/Motivo corporativo/i);
    const user = userEvent.setup();
    await user.clear(reasonInput);
    await user.type(reasonInput, "Motivo válido");

    await user.click(screen.getByRole("button", { name: /Generar etiqueta/i }));

    await waitFor(() => {
      expect(requestDeviceLabelMock).toHaveBeenCalledWith("token-123", 5, 101, "Motivo válido", {
        format: "pdf",
        template: "38x25",
      });
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
    expect(requestDeviceLabelMock).not.toHaveBeenCalled();
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

  it("permite enviar comandos directos a impresora local", async () => {
    const commandsPayload = {
      format: "zpl",
      template: "38x25",
      commands: "^XA^XZ",
      filename: "etiqueta-demo.zpl",
      content_type: "text/zpl",
      connector: { identifier: "zebra" },
      message: "Etiqueta generada para impresión directa.",
    } as const;
    requestDeviceLabelMock.mockResolvedValueOnce(commandsPayload);
    triggerDeviceLabelPrintMock.mockResolvedValueOnce({
      status: "queued",
      message: "Etiqueta encolada para impresión local.",
      details: {},
    });

    renderComponent();

    const formatSelect = screen.getByLabelText(/Formato de etiqueta/i);
    const reasonInput = screen.getByLabelText(/Motivo corporativo/i);
    const user = userEvent.setup();
    await user.selectOptions(formatSelect, "zpl");
    await user.clear(reasonInput);
    await user.type(reasonInput, "Motivo válido");

    await user.click(screen.getByRole("button", { name: /Generar etiqueta/i }));

    expect(await screen.findByText(/comandos listos/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Probar en impresora local/i }));

    await waitFor(() => {
      expect(triggerDeviceLabelPrintMock).toHaveBeenCalledWith(
        "token-123",
        5,
        101,
        "Motivo válido",
        { format: "zpl", template: "38x25", connector: { identifier: "zebra" } },
      );
    });
  });

  it("no solicita etiqueta cuando el motivo es inválido en comandos directos", async () => {
    renderComponent();

    const formatSelect = screen.getByLabelText(/Formato de etiqueta/i);
    const reasonInput = screen.getByLabelText(/Motivo corporativo/i);
    const user = userEvent.setup();
    await user.selectOptions(formatSelect, "zpl");
    await user.clear(reasonInput);
    await user.type(reasonInput, "1234");

    await user.click(screen.getByRole("button", { name: /Generar etiqueta/i }));

    expect(await screen.findByText(/al menos 5 caracteres/i)).toBeInTheDocument();
    expect(requestDeviceLabelMock).not.toHaveBeenCalled();
  });
});
