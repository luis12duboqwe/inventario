import httpClient from "./http";

export type ConfigurationParameterType = "string" | "integer" | "decimal" | "boolean" | "json";

type RawConfigurationRate = {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  value: string | number;
  unit: string;
  currency: string | null;
  effective_from: string | null;
  effective_to: string | null;
  metadata?: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type ConfigurationRate = {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  value: number;
  unit: string;
  currency: string | null;
  effective_from: string | null;
  effective_to: string | null;
  metadata: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

type RawConfigurationXmlTemplate = {
  id: number;
  code: string;
  version: string;
  description: string | null;
  namespace: string | null;
  schema_location: string | null;
  content: string;
  checksum: string;
  metadata?: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type ConfigurationXmlTemplate = {
  id: number;
  code: string;
  version: string;
  description: string | null;
  namespace: string | null;
  schema_location: string | null;
  content: string;
  checksum: string;
  metadata: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type ConfigurationParameterValue =
  | string
  | number
  | boolean
  | Record<string, unknown>
  | Array<unknown>;

type RawConfigurationParameter = {
  id: number;
  key: string;
  name: string;
  category: string | null;
  description: string | null;
  value_type: ConfigurationParameterType;
  value: unknown;
  is_sensitive: boolean;
  metadata?: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type ConfigurationParameter = {
  id: number;
  key: string;
  name: string;
  category: string | null;
  description: string | null;
  value_type: ConfigurationParameterType;
  value: ConfigurationParameterValue;
  is_sensitive: boolean;
  metadata: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

type RawConfigurationOverview = {
  rates: RawConfigurationRate[];
  xml_templates: RawConfigurationXmlTemplate[];
  parameters: RawConfigurationParameter[];
};

export type ConfigurationOverview = {
  rates: ConfigurationRate[];
  xml_templates: ConfigurationXmlTemplate[];
  parameters: ConfigurationParameter[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeRate(rate: RawConfigurationRate): ConfigurationRate {
  const parsedValue = Number.parseFloat(String(rate.value));
  return {
    ...rate,
    value: Number.isFinite(parsedValue) ? parsedValue : 0,
    metadata: rate.metadata ?? {},
  };
}

function normalizeTemplate(template: RawConfigurationXmlTemplate): ConfigurationXmlTemplate {
  return {
    ...template,
    metadata: template.metadata ?? {},
  };
}

function normalizeParameterValue(
  valueType: ConfigurationParameterType,
  value: unknown,
): ConfigurationParameterValue {
  switch (valueType) {
    case "boolean": {
      if (typeof value === "boolean") {
        return value;
      }
      const normalized = String(value ?? "").trim().toLowerCase();
      return normalized === "1" || normalized === "true" || normalized === "yes" || normalized === "si" || normalized === "sí";
    }
    case "integer": {
      const parsed = Number.parseInt(String(value ?? "0"), 10);
      return Number.isFinite(parsed) ? parsed : 0;
    }
    case "decimal": {
      const parsed = Number.parseFloat(String(value ?? "0"));
      return Number.isFinite(parsed) ? parsed : 0;
    }
    case "json": {
      if (Array.isArray(value) || isRecord(value)) {
        return value;
      }
      try {
        const parsed = JSON.parse(String(value ?? "{}"));
        if (Array.isArray(parsed) || isRecord(parsed)) {
          return parsed;
        }
      } catch (error) {
        if (import.meta.env.DEV) {
          console.warn(
            "No fue posible analizar el valor JSON del parámetro de configuración.",
            error,
          );
        }
      }
      return {};
    }
    default:
      return String(value ?? "");
  }
}

function normalizeParameter(parameter: RawConfigurationParameter): ConfigurationParameter {
  return {
    ...parameter,
    value: normalizeParameterValue(parameter.value_type, parameter.value),
    metadata: parameter.metadata ?? {},
  };
}

function normalizeOverview(data: RawConfigurationOverview): ConfigurationOverview {
  return {
    rates: data.rates.map(normalizeRate),
    xml_templates: data.xml_templates.map(normalizeTemplate),
    parameters: data.parameters.map(normalizeParameter),
  };
}

export type CreateRatePayload = {
  slug: string;
  name: string;
  description?: string | null;
  value: string;
  unit: string;
  currency?: string | null;
  effective_from?: string | null;
  effective_to?: string | null;
  metadata?: Record<string, unknown>;
};

export type UpdateRatePayload = Partial<Omit<CreateRatePayload, "slug" | "name" | "unit" | "value">> & {
  name?: string;
  unit?: string;
  value?: string;
  is_active?: boolean;
  metadata?: Record<string, unknown>;
};

export type CreateXmlTemplatePayload = {
  code: string;
  version: string;
  description?: string | null;
  namespace?: string | null;
  schema_location?: string | null;
  content: string;
  metadata?: Record<string, unknown>;
};

export type UpdateXmlTemplatePayload = Partial<Omit<CreateXmlTemplatePayload, "code">> & {
  is_active?: boolean;
};

export type CreateParameterPayload = {
  key: string;
  name: string;
  value_type: ConfigurationParameterType;
  value: unknown;
  category?: string | null;
  description?: string | null;
  is_sensitive?: boolean;
  metadata?: Record<string, unknown>;
};

export type UpdateParameterPayload = Partial<Omit<CreateParameterPayload, "key">> & {
  is_active?: boolean;
};

export async function fetchConfigurationOverview(includeInactive = true): Promise<ConfigurationOverview> {
  const response = await httpClient.get<RawConfigurationOverview>("/configuration/overview", {
    params: { include_inactive: includeInactive },
  });
  return normalizeOverview(response.data);
}

export async function createConfigurationRate(payload: CreateRatePayload, reason: string): Promise<ConfigurationRate> {
  const response = await httpClient.post<RawConfigurationRate>("/configuration/rates", payload, {
    headers: { "X-Reason": reason },
  });
  return normalizeRate(response.data);
}

export async function updateConfigurationRate(rateId: number, payload: UpdateRatePayload, reason: string): Promise<ConfigurationRate> {
  const response = await httpClient.put<RawConfigurationRate>(`/configuration/rates/${rateId}`, payload, {
    headers: { "X-Reason": reason },
  });
  return normalizeRate(response.data);
}

export async function createConfigurationXmlTemplate(payload: CreateXmlTemplatePayload, reason: string): Promise<ConfigurationXmlTemplate> {
  const response = await httpClient.post<RawConfigurationXmlTemplate>("/configuration/xml-templates", payload, {
    headers: { "X-Reason": reason },
  });
  return normalizeTemplate(response.data);
}

export async function updateConfigurationXmlTemplate(templateId: number, payload: UpdateXmlTemplatePayload, reason: string): Promise<ConfigurationXmlTemplate> {
  const response = await httpClient.put<RawConfigurationXmlTemplate>(`/configuration/xml-templates/${templateId}`, payload, {
    headers: { "X-Reason": reason },
  });
  return normalizeTemplate(response.data);
}

export async function createConfigurationParameter(payload: CreateParameterPayload, reason: string): Promise<ConfigurationParameter> {
  const response = await httpClient.post<RawConfigurationParameter>("/configuration/parameters", payload, {
    headers: { "X-Reason": reason },
  });
  return normalizeParameter(response.data);
}

export async function updateConfigurationParameter(parameterId: number, payload: UpdateParameterPayload, reason: string): Promise<ConfigurationParameter> {
  const response = await httpClient.put<RawConfigurationParameter>(`/configuration/parameters/${parameterId}`, payload, {
    headers: { "X-Reason": reason },
  });
  return normalizeParameter(response.data);
}

export async function triggerConfigurationSync(reason: string): Promise<void> {
  await httpClient.post(
    "/configuration/sync",
    {},
    {
      headers: { "X-Reason": reason },
    },
  );
}
