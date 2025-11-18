import { createHttpClient } from "./http";

export type HelpGuide = {
  module: string;
  title: string;
  summary: string;
  steps: string[];
  manual: string;
  video: string;
};

export type HelpCenterResponse = {
  guides: HelpGuide[];
  manuals_base_path: string;
  demo_mode_enabled: boolean;
};

export type DemoDataset = {
  inventory: Record<string, unknown>[];
  operations: Record<string, unknown>[];
  contacts: Record<string, unknown>[];
};

export type DemoPreview = {
  enabled: boolean;
  notice: string;
  dataset: DemoDataset | null;
};

const http = createHttpClient();

export async function fetchHelpContext(): Promise<HelpCenterResponse> {
  const { data } = await http.get<HelpCenterResponse>("/help/context");
  return data;
}

export async function fetchDemoPreview(): Promise<DemoPreview> {
  const { data } = await http.get<DemoPreview>("/help/demo");
  return data;
}
