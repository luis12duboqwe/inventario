import httpClient from "./http";

export type LanDatabaseSummary = {
  engine: string;
  location: string;
  writable: boolean;
  shared_over_lan: boolean;
};

export type LanDiscoveryResponse = {
  enabled: boolean;
  host: string;
  port: number;
  protocol: string;
  api_base_url: string;
  database: LanDatabaseSummary;
  notes: string[];
};

export async function fetchLanDiscovery(): Promise<LanDiscoveryResponse> {
  const response = await httpClient.get<LanDiscoveryResponse>("/discovery/lan");
  return response.data;
}
