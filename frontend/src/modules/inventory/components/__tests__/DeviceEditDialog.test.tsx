import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { ReactNode } from "react";
import type { Device } from "../../../../api";

vi.mock("framer-motion", async () => {
  const React = await import("react");
  const MotionDiv = React.forwardRef(
    (props: React.ComponentProps<"div">, ref: React.Ref<HTMLDivElement>) => (
      <div ref={ref} {...props} />
    ),
  );
  MotionDiv.displayName = "MotionDiv";
  const MotionButton = React.forwardRef(
    (props: React.ComponentProps<"button">, ref: React.Ref<HTMLButtonElement>) => (
      <button ref={ref} {...props} />
    ),
  );
  MotionButton.displayName = "MotionButton";

  return {
    AnimatePresence: ({ children }: { children: ReactNode }) => <>{children}</>,
    motion: {
      div: MotionDiv,
      button: MotionButton,
    },
  };
});

import DeviceEditDialog from "../DeviceEditDialog";

describe("DeviceEditDialog", () => {
  const baseDevice: Device = {
    id: 700,
    sku: "SKU-700",
    name: "Dispositivo corporativo",
    quantity: 10,
    store_id: 5,
    unit_price: 8999,
    inventory_value: 89990,
    completo: true,
    imei: "490154203237517",
    serial: "SER-700",
    marca: "Softmobile",
    modelo: "SM-700",
    categoria: "Smartphones",
    condicion: "Nuevo",
    color: "Azul",
    capacidad_gb: 128,
    capacidad: "128 GB",
    estado_comercial: "nuevo",
    estado: "disponible",
    proveedor: "Softmobile Corp",
    costo_unitario: 7000,
    costo_compra: 7000,
    margen_porcentaje: 22,
    garantia_meses: 12,
    lote: "LOT-700",
    fecha_compra: "2025-01-05",
    fecha_ingreso: "2025-01-06",
    ubicacion: "Bodega",
    descripcion: "Equipo corporativo listo para venta",
    imagen_url: "https://softmobile.test/devices/sku-700.png",
    imeis_adicionales: ["490154203237510"],
    imagenes: ["https://softmobile.test/devices/sku-700-front.png"],
    enlaces: [{ titulo: "Ficha", url: "https://softmobile.test/ficha.pdf" }],
    precio_venta: 8999,
    identifier: null,
  };

  it("normaliza campos con listas y enlaces antes de enviar", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    render(<DeviceEditDialog device={baseDevice} open onClose={onClose} onSubmit={onSubmit} />);

    const nameInput = await screen.findByLabelText("Nombre comercial");
    await user.clear(nameInput);
    await user.type(nameInput, "Dispositivo actualizado");

    const imeiInput = screen.getByLabelText(/^IMEI$/i);
    await user.clear(imeiInput);
    await user.type(imeiInput, "490154203237520");

    const imeisTextarea = screen.getByPlaceholderText("Ingresa un IMEI por línea");
    await user.clear(imeisTextarea);
    await user.type(imeisTextarea, "490154203237521\n\n490154203237521\n  490154203237522  ");

    const imagesTextarea = screen.getByPlaceholderText("https://cdn.softmobile.test/foto.png");
    await user.clear(imagesTextarea);
    await user.type(
      imagesTextarea,
      "https://softmobile.test/devices/sku-700-back.png\n \nhttps://softmobile.test/devices/sku-700-box.png",
    );

    const linksTextarea = screen.getByPlaceholderText("Manual|https://softmobile.test/manual.pdf");
    await user.clear(linksTextarea);
    await user.type(
      linksTextarea,
      "Manual|https://softmobile.test/manual.pdf\n\nhttps://softmobile.test/soporte",
    );

    const descriptionTextarea = screen.getByLabelText("Descripción");
    await user.clear(descriptionTextarea);
    await user.type(descriptionTextarea, "Equipo con accesorios completos");

    const reasonTextarea = screen.getByLabelText("Motivo corporativo");
    await user.type(reasonTextarea, "Actualización integral del catálogo");

    const submitButton = screen.getByRole("button", { name: /Guardar cambios/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalled();
    });

    const [updates, reason] = onSubmit.mock.calls[0]!;
    expect(reason).toBe("Actualización integral del catálogo");
    expect(updates).toMatchObject({
      name: "Dispositivo actualizado",
      imei: "490154203237520",
      descripcion: "Equipo con accesorios completos",
      imeis_adicionales: ["490154203237521", "490154203237521", "490154203237522"],
      imagenes: [
        "https://softmobile.test/devices/sku-700-back.png",
        "https://softmobile.test/devices/sku-700-box.png",
      ],
      enlaces: [
        { titulo: "Manual", url: "https://softmobile.test/manual.pdf" },
        { titulo: "Recurso", url: "https://softmobile.test/soporte" },
      ],
    });
    expect(onClose).toHaveBeenCalled();
  });

  it("exige un motivo corporativo válido antes de enviar", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    render(<DeviceEditDialog device={baseDevice} open onClose={onClose} onSubmit={onSubmit} />);

    const descriptionTextarea = await screen.findByLabelText("Descripción");
    await user.clear(descriptionTextarea);
    await user.type(descriptionTextarea, "Actualización menor");

    const reasonTextarea = screen.getByLabelText("Motivo corporativo");
    await user.type(reasonTextarea, "1234");

    const submitButton = screen.getByRole("button", { name: /Guardar cambios/i });
    await user.click(submitButton);

    expect(
      await screen.findByText("Ingresa un motivo corporativo de al menos 5 caracteres."),
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
    expect(onClose).not.toHaveBeenCalled();
  });
});
