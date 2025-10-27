import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getApiBaseUrl } from "../../../../config/api";

import type { CatalogDevice } from "../../../../api";

const API_BASE_URL = (import.meta.env.VITE_API_URL?.trim() ?? "") || getApiBaseUrl();

const buildImageUrl = (path: string): string => new URL(path, API_BASE_URL).toString();

const searchCatalogDevicesMock = vi.hoisted(() => vi.fn());

const apiModuleId = vi.hoisted(
  () => new URL("../../../../api.ts", import.meta.url).pathname,
);

vi.mock("../../../../api", () => ({
  __esModule: true,
  searchCatalogDevices: searchCatalogDevicesMock,
}));

vi.mock(apiModuleId, () => ({
  __esModule: true,
  searchCatalogDevices: searchCatalogDevicesMock,
}));

import AdvancedSearch from "../AdvancedSearch";

describe("AdvancedSearch", () => {
  beforeEach(() => {
    searchCatalogDevicesMock.mockReset();
  });

  it("muestra un error cuando no se proporcionan filtros", async () => {
    const user = userEvent.setup();
    render(<AdvancedSearch token="token-123" />);

    const submitButton = screen.getByRole("button", { name: /buscar/i });
    await user.click(submitButton);

    expect(
      await screen.findByText("Ingresa al menos un criterio de búsqueda"),
    ).toBeInTheDocument();
    expect(searchCatalogDevicesMock).not.toHaveBeenCalled();
  });

  it("renderiza los resultados devueltos por la API", async () => {
    const user = userEvent.setup();
    const deviceResults: CatalogDevice[] = [
      {
        id: 200,
        sku: "IPH-15-PRO",
        name: "iPhone 15 Pro",
        quantity: 4,
        store_id: 2,
        unit_price: 23999,
        inventory_value: 95996,
        store_name: "Sucursal Norte",
        imei: "490154203237517",
        serial: "SER-IPH-15",
        marca: "Apple",
        modelo: "iPhone 15 Pro",
        color: "Negro",
        capacidad_gb: 256,
        estado_comercial: "nuevo",
        categoria: "Smartphones",
        condicion: "Nuevo",
        estado: "disponible",
        ubicacion: "Vitrina",
        fecha_ingreso: "2025-02-12",
        proveedor: "Apple",
        costo_unitario: 20000,
        costo_compra: 20000,
        precio_venta: 23999,
        margen_porcentaje: 18,
        garantia_meses: 12,
        lote: "L-15P-2025",
        fecha_compra: "2025-02-10",
        descripcion: "Equipo sellado",
        imagen_url: buildImageUrl("/media/devices/iphone15pro.png"),
      },
    ];

    searchCatalogDevicesMock.mockResolvedValueOnce(deviceResults);

    render(<AdvancedSearch token="token-123" />);

    const modelInput = screen.getByLabelText("Modelo");
    await user.type(modelInput, "iPhone 15 Pro");

    const submitButton = screen.getByRole("button", { name: /buscar/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(searchCatalogDevicesMock).toHaveBeenCalledWith("token-123", {
        imei: "",
        serial: "",
        capacidad_gb: undefined,
        color: "",
        marca: "",
        modelo: "iPhone 15 Pro",
        categoria: undefined,
        condicion: undefined,
        estado: undefined,
        ubicacion: undefined,
        proveedor: undefined,
        fecha_ingreso_desde: undefined,
        fecha_ingreso_hasta: undefined,
      });
    });

    expect(await screen.findByText("Sucursal Norte")).toBeInTheDocument();
    expect(screen.getByText("iPhone 15 Pro")).toBeInTheDocument();
    expect(screen.getByText("Negro")).toBeInTheDocument();
    expect(screen.getByText("Smartphones")).toBeInTheDocument();
    expect(
      screen.queryByText("Ingresa al menos un criterio de búsqueda"),
    ).not.toBeInTheDocument();
  });
});

