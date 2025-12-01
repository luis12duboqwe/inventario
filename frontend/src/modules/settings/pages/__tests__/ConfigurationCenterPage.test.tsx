import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import * as configurationApi from "@api/configuration";
import * as discoveryApi from "@api/discovery";
import ConfigurationCenterPage from "../ConfigurationCenterPage";

vi.mock("../../../dashboard/context/DashboardContext", () => ({
  __esModule: true,
  useDashboard: () => ({
    pushToast: vi.fn(),
  }),
}));

const overviewMock = {
  rates: [
    {
      id: 1,
      slug: "iva_general",
      name: "IVA general",
      description: "",
      value: 0.16,
      unit: "porcentaje",
      currency: "MXN",
      effective_from: null,
      effective_to: null,
      metadata: { autoridad: "SAT" },
      is_active: true,
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
    },
  ],
  xml_templates: [
    {
      id: 2,
      code: "sar_envio_inicial",
      version: "v1.0",
      description: "",
      namespace: "https://softmobile.mx/sar",
      schema_location: "https://softmobile.mx/sar/schema.xsd",
      content: "<sar />",
      checksum: "abc",
      metadata: {},
      is_active: true,
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
    },
  ],
  parameters: [
    {
      id: 3,
      key: "sar_endpoint",
      name: "Endpoint SAR",
      category: null,
      description: null,
      value_type: "string" as const,
      value: "https://sar.example.com",
      is_sensitive: false,
      metadata: {},
      is_active: true,
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
    },
  ],
};

vi.spyOn(configurationApi, "fetchConfigurationOverview").mockResolvedValue(overviewMock);
vi.spyOn(discoveryApi, "fetchLanDiscovery").mockResolvedValue({
  enabled: true,
  host: "192.168.0.10",
  port: 8000,
  protocol: "http",
  api_base_url: "http://192.168.0.10:8000/api",
  database: {
    engine: "sqlite",
    location: "/data/softmobile.db",
    writable: true,
    shared_over_lan: true,
  },
  notes: ["LAN activa"],
});

describe("ConfigurationCenterPage", () => {
  it("muestra tasas, plantillas y parámetros", async () => {
    const client = new QueryClient();
    client.setQueryData(["configuration-overview"], overviewMock);
    render(
      <QueryClientProvider client={client}>
        <ConfigurationCenterPage />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Asistente LAN")).toBeInTheDocument();
    expect(await screen.findByText("Tasas configurables")).toBeInTheDocument();
    expect(await screen.findByText("iva_general")).toBeInTheDocument();
    expect(await screen.findByText("sar_envio_inicial")).toBeInTheDocument();
    expect(await screen.findByText("sar_endpoint")).toBeInTheDocument();
  });
});
