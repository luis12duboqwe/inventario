import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Device } from "../../../../api";

const downloadDeviceLabelPdfMock = vi.hoisted(() => vi.fn());
const generateInventoryBarcodeMock = vi.hoisted(() => vi.fn());

const apiModuleId = vi.hoisted(
  () => new URL("../../../../api.ts", import.meta.url).pathname,
);

vi.mock("../../../../api", () => ({
  __esModule: true,
  downloadDeviceLabelPdf: downloadDeviceLabelPdfMock,
  generateInventoryBarcode: generateInventoryBarcodeMock,
}));

vi.mock(apiModuleId, () => ({
  __esModule: true,
  downloadDeviceLabelPdf: downloadDeviceLabelPdfMock,
  generateInventoryBarcode: generateInventoryBarcodeMock,
}));

import LabelPrinter from "../LabelPrinter";

describe("LabelPrinter", () => {
  const baseDevice: Device = {
    id: 101,
    sku: "SKU-101",
    name: "Equipo demo",
    quantity: 5,
    store_id: 3,
    unit_price: 15999,
    inventory_value: 79995,
    completo: true,
    imei: "490154203237517",
    serial: "SER-101",
    marca: "Softmobile",
    modelo: "Demo Pro",
    categoria: "Smartphones",
    condicion: "Nuevo",
    color: "Negro",
    capacidad_gb: 256,
    capacidad: "256 GB",
    estado_comercial: "nuevo",
    estado: "disponible",
    proveedor: "Proveedor Demo",
    costo_unitario: 13000,
    costo_compra: 13000,
    margen_porcentaje: 19,
    garantia_meses: 12,
    lote: "L-2025-01",
    fecha_compra: "2025-01-10",
    fecha_ingreso: "2025-01-11",
    ubicacion: "Vitrina",
    descripcion: "Equipo listo para demostraciones",
    imagen_url: "https://softmobile.test/images/demo.png",
    imeis_adicionales: ["490154203237518", "  "],
    imagenes: [
      "https://softmobile.test/images/demo-frontal.png",
      "",
      "https://softmobile.test/images/demo-lateral.png",
    ],
    enlaces: [
      { titulo: "Manual", url: "https://softmobile.test/manual.pdf" },
      { titulo: "", url: "https://softmobile.test/soporte" },
    ],
    precio_venta: 15999,
    identifier: null,
  };

  beforeEach(() => {
    downloadDeviceLabelPdfMock.mockReset();
    generateInventoryBarcodeMock.mockReset();
  });

  it("muestra el resumen y genera el código de barras", async () => {
    const user = userEvent.setup();
    generateInventoryBarcodeMock.mockResolvedValueOnce({
      data: "ZGF0YQ==",
      mime_type: "image/png",
      width: 320,
      height: 120,
    });

    render(
      <LabelPrinter
        open
        onClose={vi.fn()}
        device={baseDevice}
        storeId={baseDevice.store_id}
        storeName="Sucursal Centro"
        token="token-123"
      />,
    );

    expect(screen.getByText("IMEI registrados")).toBeInTheDocument();
    expect(screen.getByText("Imágenes")).toBeInTheDocument();
    expect(screen.getByText("https://softmobile.test/manual.pdf")).toBeInTheDocument();
    expect(screen.getByText("https://softmobile.test/soporte")).toBeInTheDocument();

    const valueInput = screen.getByLabelText("Valor a codificar");
    await user.clear(valueInput);
    await user.type(valueInput, "SKU-101");

    const generateButton = screen.getByRole("button", { name: /Generar código/i });
    await user.click(generateButton);

    await waitFor(() => {
      expect(generateInventoryBarcodeMock).toHaveBeenCalledWith(
        "token-123",
        { valor: "SKU-101", formato: "code128" },
        "Impresión de etiqueta de inventario",
      );
    });

    expect(
      await screen.findByAltText("Vista previa code128"),
    ).toBeInTheDocument();
    expect(screen.getByText("320 × 120 px")).toBeInTheDocument();
  });

  it("descarga la etiqueta en PDF y conserva el enlace de acceso", async () => {
    const user = userEvent.setup();
    const blob = new Blob(["contenido"], { type: "application/pdf" });
    downloadDeviceLabelPdfMock.mockResolvedValueOnce({
      blob,
      filename: "etiqueta-demo.pdf",
    });

    const originalCreateObjectURL = global.URL.createObjectURL;
    const originalRevokeObjectURL = global.URL.revokeObjectURL;
    const createObjectURLMock = vi.fn(() => "blob:demo");
    const revokeObjectURLMock = vi.fn();
    Object.defineProperty(global.URL, "createObjectURL", {
      configurable: true,
      value: createObjectURLMock,
    });
    Object.defineProperty(global.URL, "revokeObjectURL", {
      configurable: true,
      value: revokeObjectURLMock,
    });
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});

    render(
      <LabelPrinter
        open
        onClose={vi.fn()}
        device={baseDevice}
        storeId={baseDevice.store_id}
        storeName="Sucursal Centro"
        token="token-123"
      />,
    );

    const reasonTextarea = screen.getByLabelText(/Motivo corporativo/i);
    await user.clear(reasonTextarea);
    await user.type(reasonTextarea, "Motivo válido");

    const templateSelect = screen.getByLabelText("Plantilla de etiqueta");
    await user.selectOptions(templateSelect, "detallada");

    const downloadButton = screen.getByRole("button", {
      name: /Descargar etiqueta PDF/i,
    });
    await user.click(downloadButton);

    await waitFor(() => {
      expect(downloadDeviceLabelPdfMock).toHaveBeenCalledWith(
        "token-123",
        baseDevice.store_id,
        baseDevice.id,
        "Motivo válido",
        { template: "detallada" },
      );
    });

    expect(createObjectURLMock).toHaveBeenCalledWith(blob);
    expect(clickSpy).toHaveBeenCalled();
    expect(
      await screen.findByRole("link", { name: "etiqueta-demo.pdf" }),
    ).toBeInTheDocument();

    clickSpy.mockRestore();
    Object.defineProperty(global.URL, "createObjectURL", {
      configurable: true,
      value: originalCreateObjectURL,
    });
    Object.defineProperty(global.URL, "revokeObjectURL", {
      configurable: true,
      value: originalRevokeObjectURL,
    });
  });
});
