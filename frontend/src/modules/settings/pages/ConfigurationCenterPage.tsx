import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import PageHeader from "../../../shared/components/ui/PageHeader";
import Button from "../../../shared/components/ui/Button";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import {
  type ConfigurationOverview,
  type ConfigurationRate,
  type ConfigurationXmlTemplate,
  type ConfigurationParameter,
  type ConfigurationParameterType,
  createConfigurationParameter,
  createConfigurationRate,
  createConfigurationXmlTemplate,
  fetchConfigurationOverview,
  triggerConfigurationSync,
  updateConfigurationParameter,
  updateConfigurationRate,
  updateConfigurationXmlTemplate,
} from "../../../services/api/configuration";

type RateFormState = {
  slug: string;
  name: string;
  description: string;
  value: string;
  unit: string;
  currency: string;
  effectiveFrom: string;
  effectiveTo: string;
  metadata: string;
};

type TemplateFormState = {
  code: string;
  version: string;
  description: string;
  namespace: string;
  schemaLocation: string;
  content: string;
  metadata: string;
};

type ParameterFormState = {
  key: string;
  name: string;
  valueType: ConfigurationParameterType;
  value: string;
  category: string;
  description: string;
  metadata: string;
  isSensitive: boolean;
};

const emptyRateForm: RateFormState = {
  slug: "",
  name: "",
  description: "",
  value: "0.0000",
  unit: "porcentaje",
  currency: "MXN",
  effectiveFrom: "",
  effectiveTo: "",
  metadata: "{}",
};

const emptyTemplateForm: TemplateFormState = {
  code: "",
  version: "v1.0",
  description: "",
  namespace: "",
  schemaLocation: "",
  content: "<sar version=\"1.0\"></sar>",
  metadata: "{}",
};

const emptyParameterForm: ParameterFormState = {
  key: "",
  name: "",
  valueType: "string",
  value: "",
  category: "",
  description: "",
  metadata: "{}",
  isSensitive: false,
};

const DECIMAL_PATTERN = /^-?\d+(\.\d{1,4})?$/;
const INTEGER_PATTERN = /^-?\d+$/;

function parseMetadata(raw: string): Record<string, unknown> {
  const trimmed = raw.trim();
  if (!trimmed) {
    return {};
  }
  try {
    const parsed = JSON.parse(trimmed);
    if (parsed && typeof parsed === "object") {
      return parsed as Record<string, unknown>;
    }
  } catch (error) {
    throw new Error("Metadatos inválidos, utiliza JSON válido.");
  }
  throw new Error("Metadatos inválidos, utiliza JSON válido.");
}

function formatMetadata(metadata: Record<string, unknown> | undefined): string {
  if (!metadata || Object.keys(metadata).length === 0) {
    return "{}";
  }
  try {
    return JSON.stringify(metadata, null, 2);
  } catch {
    return "{}";
  }
}

function ensureReason(
  reason: string,
  notify: (message: string, variant?: "success" | "error" | "warning" | "info") => void,
): string | null {
  const normalized = reason.trim();
  if (normalized.length < 5) {
    notify("Indica un motivo corporativo de al menos 5 caracteres.", "warning");
    return null;
  }
  return normalized;
}

function normalizeParameterValue(valueType: ConfigurationParameterType, raw: string): unknown {
  const trimmed = raw.trim();
  switch (valueType) {
    case "boolean":
      return trimmed.toLowerCase() === "true" || trimmed === "1";
    case "integer":
      return Number.parseInt(trimmed || "0", 10);
    case "decimal":
      return trimmed;
    case "json":
      return parseMetadata(trimmed || "{}");
    default:
      return trimmed;
  }
}

function stringifyParameterValue(parameter: ConfigurationParameter): string {
  if (parameter.value_type === "json") {
    try {
      return JSON.stringify(parameter.value, null, 2);
    } catch {
      return "{}";
    }
  }
  if (parameter.value_type === "decimal" && typeof parameter.value === "number") {
    return parameter.value.toFixed(4);
  }
  return String(parameter.value ?? "");
}

function formatDecimal(value: number): string {
  return Number.isFinite(value) ? value.toFixed(4) : "0.0000";
}

export default function ConfigurationCenterPage(): JSX.Element {
  const { pushToast } = useDashboard();
  const queryClient = useQueryClient();
  const [rateForm, setRateForm] = useState<RateFormState>(emptyRateForm);
  const [templateForm, setTemplateForm] = useState<TemplateFormState>(emptyTemplateForm);
  const [parameterForm, setParameterForm] = useState<ParameterFormState>(emptyParameterForm);
  const [rateReason, setRateReason] = useState("Actualización tasas SAR");
  const [templateReason, setTemplateReason] = useState("Actualización plantillas SAR");
  const [parameterReason, setParameterReason] = useState("Ajuste parámetros SAR");
  const [syncReason, setSyncReason] = useState("Sincronización YAML SAR");
  const [editingRate, setEditingRate] = useState<ConfigurationRate | null>(null);
  const [editingTemplate, setEditingTemplate] = useState<ConfigurationXmlTemplate | null>(null);
  const [editingParameter, setEditingParameter] = useState<ConfigurationParameter | null>(null);

  const overviewQuery = useQuery<ConfigurationOverview>({
    queryKey: ["configuration-overview"],
    queryFn: () => fetchConfigurationOverview(true),
  });

  const notify = (message: string, variant: "success" | "error" | "warning" | "info" = "info") => {
    pushToast({ message, variant });
  };

  const invalidateOverview = async () => {
    await queryClient.invalidateQueries({ queryKey: ["configuration-overview"] });
  };

  const rateMutation = useMutation({
    mutationFn: async (reason: string) => {
      const metadata = parseMetadata(rateForm.metadata);
      if (editingRate) {
        return updateConfigurationRate(
          editingRate.id,
          {
            name: rateForm.name,
            description: rateForm.description || null,
            value: rateForm.value,
            unit: rateForm.unit,
            currency: rateForm.currency || null,
            effective_from: rateForm.effectiveFrom || null,
            effective_to: rateForm.effectiveTo || null,
            metadata,
          },
          reason,
        );
      }
      return createConfigurationRate(
        {
          slug: rateForm.slug,
          name: rateForm.name,
          description: rateForm.description || null,
          value: rateForm.value,
          unit: rateForm.unit,
          currency: rateForm.currency || null,
          effective_from: rateForm.effectiveFrom || null,
          effective_to: rateForm.effectiveTo || null,
          metadata,
        },
        reason,
      );
    },
    onSuccess: async (rate) => {
      await invalidateOverview();
      setEditingRate(null);
      setRateForm(emptyRateForm);
      notify(`Tasa ${rate.name} registrada correctamente.`, "success");
    },
    onError: () => {
      notify("No fue posible guardar la tasa, revisa los datos ingresados.", "error");
    },
  });

  const templateMutation = useMutation({
    mutationFn: async (reason: string) => {
      const metadata = parseMetadata(templateForm.metadata);
      if (editingTemplate) {
        return updateConfigurationXmlTemplate(
          editingTemplate.id,
          {
            version: templateForm.version,
            description: templateForm.description || null,
            namespace: templateForm.namespace || null,
            schema_location: templateForm.schemaLocation || null,
            content: templateForm.content,
            metadata,
          },
          reason,
        );
      }
      return createConfigurationXmlTemplate(
        {
          code: templateForm.code,
          version: templateForm.version,
          description: templateForm.description || null,
          namespace: templateForm.namespace || null,
          schema_location: templateForm.schemaLocation || null,
          content: templateForm.content,
          metadata,
        },
        reason,
      );
    },
    onSuccess: async (template) => {
      await invalidateOverview();
      setEditingTemplate(null);
      setTemplateForm(emptyTemplateForm);
      notify(`Plantilla ${template.code} actualizada.`, "success");
    },
    onError: () => {
      notify("No fue posible guardar la plantilla XML.", "error");
    },
  });

  const parameterMutation = useMutation({
    mutationFn: async (reason: string) => {
      const metadata = parseMetadata(parameterForm.metadata);
      const value = normalizeParameterValue(parameterForm.valueType, parameterForm.value);
      if (editingParameter) {
        return updateConfigurationParameter(
          editingParameter.id,
          {
            name: parameterForm.name,
            value_type: parameterForm.valueType,
            value,
            category: parameterForm.category || null,
            description: parameterForm.description || null,
            metadata,
            is_sensitive: parameterForm.isSensitive,
          },
          reason,
        );
      }
      return createConfigurationParameter(
        {
          key: parameterForm.key,
          name: parameterForm.name,
          value_type: parameterForm.valueType,
          value,
          category: parameterForm.category || null,
          description: parameterForm.description || null,
          metadata,
          is_sensitive: parameterForm.isSensitive,
        },
        reason,
      );
    },
    onSuccess: async (parameter) => {
      await invalidateOverview();
      setEditingParameter(null);
      setParameterForm(emptyParameterForm);
      notify(`Parámetro ${parameter.key} actualizado.`, "success");
    },
    onError: () => {
      notify("No fue posible guardar el parámetro.", "error");
    },
  });

  const syncMutation = useMutation({
    mutationFn: (reason: string) => triggerConfigurationSync(reason),
    onSuccess: async () => {
      await invalidateOverview();
      notify("Sincronización ejecutada correctamente.", "success");
    },
    onError: () => {
      notify("No fue posible sincronizar la configuración.", "error");
    },
  });

  const handleRateSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const reason = ensureReason(rateReason, notify);
    if (!reason) {
      return;
    }
    if (!DECIMAL_PATTERN.test(rateForm.value.trim())) {
      notify("Ingresa un valor decimal válido con hasta cuatro decimales.", "warning");
      return;
    }
    rateMutation.mutate(reason);
  };

  const handleTemplateSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const reason = ensureReason(templateReason, notify);
    if (!reason) {
      return;
    }
    templateMutation.mutate(reason);
  };

  const handleParameterSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const reason = ensureReason(parameterReason, notify);
    if (!reason) {
      return;
    }
    const trimmedValue = parameterForm.value.trim();
    if (parameterForm.valueType === "integer" && !INTEGER_PATTERN.test(trimmedValue)) {
      notify("Ingresa un número entero válido para el parámetro.", "warning");
      return;
    }
    if (parameterForm.valueType === "decimal" && !DECIMAL_PATTERN.test(trimmedValue)) {
      notify("Ingresa un valor decimal válido para el parámetro.", "warning");
      return;
    }
    parameterMutation.mutate(reason);
  };

  const handleSync = () => {
    const reason = ensureReason(syncReason, notify);
    if (!reason) {
      return;
    }
    syncMutation.mutate(reason);
  };

  const overview = overviewQuery.data;
  const rates = useMemo(() => overview?.rates ?? [], [overview]);
  const xmlTemplates = useMemo(() => overview?.xml_templates ?? [], [overview]);
  const parameters = useMemo(() => overview?.parameters ?? [], [overview]);
  const loading = overviewQuery.isLoading;

  return (
    <div className="configuration-center">
      <PageHeader
        title="Configuración SAR y fiscal"
        subtitle="Centraliza tasas, plantillas XML y parámetros de cumplimiento sin desplegar nuevas versiones."
      />

      <section className="card configuration-card">
        <header className="configuration-card__header">
          <div>
            <h2>Sincronización desde YAML</h2>
            <p>Aplica los cambios almacenados en <code>ops/config_sync</code> sin reiniciar servicios.</p>
          </div>
          <div className="configuration-sync">
            <label className="configuration-sync__label" htmlFor="sync-reason">
              Motivo corporativo
            </label>
            <input
              id="sync-reason"
              className="configuration-input"
              value={syncReason}
              onChange={(event) => setSyncReason(event.target.value)}
              placeholder="Describe el motivo"
            />
            <Button onClick={handleSync} disabled={syncMutation.isLoading} variant="primary">
              {syncMutation.isLoading ? "Sincronizando…" : "Sincronizar"}
            </Button>
          </div>
        </header>
      </section>

      <section className="card configuration-card">
        <header className="configuration-card__header">
          <div>
            <h2>Tasas configurables</h2>
            <p>Administra tasas de impuestos, retenciones y factores SAR.</p>
          </div>
        </header>

        <div className="configuration-grid">
          <form className="configuration-form" onSubmit={handleRateSubmit}>
            <fieldset>
              <legend>{editingRate ? `Editar ${editingRate.name}` : "Registrar tasa"}</legend>
              {!editingRate && (
                <label>
                  Slug
                  <input
                    className="configuration-input"
                    value={rateForm.slug}
                    onChange={(event) => setRateForm((current) => ({ ...current, slug: event.target.value }))}
                    required
                  />
                </label>
              )}
              <label>
                Nombre
                <input
                  className="configuration-input"
                  value={rateForm.name}
                  onChange={(event) => setRateForm((current) => ({ ...current, name: event.target.value }))}
                  required
                />
              </label>
              <label>
                Descripción
                <textarea
                  className="configuration-textarea"
                  value={rateForm.description}
                  onChange={(event) => setRateForm((current) => ({ ...current, description: event.target.value }))}
                  rows={2}
                />
              </label>
              <div className="configuration-row">
                <label>
                  Valor
                  <input
                    className="configuration-input"
                    value={rateForm.value}
                    onChange={(event) => setRateForm((current) => ({ ...current, value: event.target.value }))}
                    required
                  />
                </label>
                <label>
                  Unidad
                  <input
                    className="configuration-input"
                    value={rateForm.unit}
                    onChange={(event) => setRateForm((current) => ({ ...current, unit: event.target.value }))}
                    required
                  />
                </label>
                <label>
                  Moneda
                  <input
                    className="configuration-input"
                    value={rateForm.currency}
                    onChange={(event) => setRateForm((current) => ({ ...current, currency: event.target.value }))}
                  />
                </label>
              </div>
              <div className="configuration-row">
                <label>
                  Vigente desde
                  <input
                    type="datetime-local"
                    className="configuration-input"
                    value={rateForm.effectiveFrom}
                    onChange={(event) => setRateForm((current) => ({ ...current, effectiveFrom: event.target.value }))}
                  />
                </label>
                <label>
                  Vigente hasta
                  <input
                    type="datetime-local"
                    className="configuration-input"
                    value={rateForm.effectiveTo}
                    onChange={(event) => setRateForm((current) => ({ ...current, effectiveTo: event.target.value }))}
                  />
                </label>
              </div>
              <label>
                Metadatos (JSON)
                <textarea
                  className="configuration-textarea"
                  value={rateForm.metadata}
                  onChange={(event) => setRateForm((current) => ({ ...current, metadata: event.target.value }))}
                  rows={3}
                />
              </label>
              <label>
                Motivo corporativo
                <input
                  className="configuration-input"
                  value={rateReason}
                  onChange={(event) => setRateReason(event.target.value)}
                  required
                />
              </label>
              <div className="configuration-actions">
                <Button type="submit" variant="primary" disabled={rateMutation.isLoading}>
                  {rateMutation.isLoading ? "Guardando…" : editingRate ? "Actualizar tasa" : "Registrar tasa"}
                </Button>
                {editingRate ? (
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => {
                      setEditingRate(null);
                      setRateForm(emptyRateForm);
                    }}
                  >
                    Cancelar
                  </Button>
                ) : null}
              </div>
            </fieldset>
          </form>

          <div className="configuration-table-container" role="region" aria-live="polite">
            {loading ? (
              <p className="configuration-empty">Cargando tasas…</p>
            ) : rates.length === 0 ? (
              <p className="configuration-empty">No hay tasas registradas.</p>
            ) : (
              <table className="configuration-table">
                <thead>
                  <tr>
                    <th>Slug</th>
                    <th>Nombre</th>
                    <th>Valor</th>
                    <th>Unidad</th>
                    <th>Estado</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {rates.map((rate) => (
                    <tr key={rate.id}>
                      <td>{rate.slug}</td>
                      <td>{rate.name}</td>
                      <td>{formatDecimal(rate.value)}</td>
                      <td>{rate.unit}</td>
                      <td>
                        <span className={rate.is_active ? "status-pill tone-info" : "status-pill tone-warning"}>
                          {rate.is_active ? "Activa" : "Inactiva"}
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="configuration-link"
                          onClick={() => {
                            setEditingRate(rate);
                            setRateForm({
                              slug: rate.slug,
                              name: rate.name,
                              description: rate.description ?? "",
                              value: formatDecimal(rate.value),
                              unit: rate.unit,
                              currency: rate.currency ?? "",
                              effectiveFrom: rate.effective_from ?? "",
                              effectiveTo: rate.effective_to ?? "",
                              metadata: formatMetadata(rate.metadata),
                            });
                          }}
                        >
                          Editar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </section>

      <section className="card configuration-card">
        <header className="configuration-card__header">
          <div>
            <h2>Plantillas XML SAR</h2>
            <p>Gestiona las estructuras XML consumidas por los procesos SAR.</p>
          </div>
        </header>

        <div className="configuration-grid">
          <form className="configuration-form" onSubmit={handleTemplateSubmit}>
            <fieldset>
              <legend>{editingTemplate ? `Editar ${editingTemplate.code}` : "Registrar plantilla"}</legend>
              {!editingTemplate && (
                <label>
                  Código
                  <input
                    className="configuration-input"
                    value={templateForm.code}
                    onChange={(event) => setTemplateForm((current) => ({ ...current, code: event.target.value }))}
                    required
                  />
                </label>
              )}
              <label>
                Versión
                <input
                  className="configuration-input"
                  value={templateForm.version}
                  onChange={(event) => setTemplateForm((current) => ({ ...current, version: event.target.value }))}
                  required
                />
              </label>
              <label>
                Descripción
                <textarea
                  className="configuration-textarea"
                  value={templateForm.description}
                  onChange={(event) => setTemplateForm((current) => ({ ...current, description: event.target.value }))}
                  rows={2}
                />
              </label>
              <div className="configuration-row">
                <label>
                  Namespace
                  <input
                    className="configuration-input"
                    value={templateForm.namespace}
                    onChange={(event) => setTemplateForm((current) => ({ ...current, namespace: event.target.value }))}
                  />
                </label>
                <label>
                  Schema location
                  <input
                    className="configuration-input"
                    value={templateForm.schemaLocation}
                    onChange={(event) => setTemplateForm((current) => ({ ...current, schemaLocation: event.target.value }))}
                  />
                </label>
              </div>
              <label>
                Contenido XML
                <textarea
                  className="configuration-textarea"
                  value={templateForm.content}
                  onChange={(event) => setTemplateForm((current) => ({ ...current, content: event.target.value }))}
                  rows={6}
                  required
                />
              </label>
              <label>
                Metadatos (JSON)
                <textarea
                  className="configuration-textarea"
                  value={templateForm.metadata}
                  onChange={(event) => setTemplateForm((current) => ({ ...current, metadata: event.target.value }))}
                  rows={3}
                />
              </label>
              <label>
                Motivo corporativo
                <input
                  className="configuration-input"
                  value={templateReason}
                  onChange={(event) => setTemplateReason(event.target.value)}
                  required
                />
              </label>
              <div className="configuration-actions">
                <Button type="submit" variant="primary" disabled={templateMutation.isLoading}>
                  {templateMutation.isLoading ? "Guardando…" : editingTemplate ? "Actualizar plantilla" : "Registrar plantilla"}
                </Button>
                {editingTemplate ? (
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => {
                      setEditingTemplate(null);
                      setTemplateForm(emptyTemplateForm);
                    }}
                  >
                    Cancelar
                  </Button>
                ) : null}
              </div>
            </fieldset>
          </form>

          <div className="configuration-table-container" role="region" aria-live="polite">
            {loading ? (
              <p className="configuration-empty">Cargando plantillas…</p>
            ) : xmlTemplates.length === 0 ? (
              <p className="configuration-empty">No hay plantillas registradas.</p>
            ) : (
              <table className="configuration-table">
                <thead>
                  <tr>
                    <th>Código</th>
                    <th>Versión</th>
                    <th>Estado</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {xmlTemplates.map((template) => (
                    <tr key={template.id}>
                      <td>{template.code}</td>
                      <td>{template.version}</td>
                      <td>
                        <span className={template.is_active ? "status-pill tone-info" : "status-pill tone-warning"}>
                          {template.is_active ? "Activa" : "Inactiva"}
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="configuration-link"
                          onClick={() => {
                            setEditingTemplate(template);
                            setTemplateForm({
                              code: template.code,
                              version: template.version,
                              description: template.description ?? "",
                              namespace: template.namespace ?? "",
                              schemaLocation: template.schema_location ?? "",
                              content: template.content,
                              metadata: formatMetadata(template.metadata),
                            });
                          }}
                        >
                          Editar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </section>

      <section className="card configuration-card">
        <header className="configuration-card__header">
          <div>
            <h2>Parámetros operativos</h2>
            <p>Define parámetros SAR que afectan procesos de sincronización y envíos.</p>
          </div>
        </header>

        <div className="configuration-grid">
          <form className="configuration-form" onSubmit={handleParameterSubmit}>
            <fieldset>
              <legend>{editingParameter ? `Editar ${editingParameter.key}` : "Registrar parámetro"}</legend>
              {!editingParameter && (
                <label>
                  Clave
                  <input
                    className="configuration-input"
                    value={parameterForm.key}
                    onChange={(event) => setParameterForm((current) => ({ ...current, key: event.target.value }))}
                    required
                  />
                </label>
              )}
              <label>
                Nombre
                <input
                  className="configuration-input"
                  value={parameterForm.name}
                  onChange={(event) => setParameterForm((current) => ({ ...current, name: event.target.value }))}
                  required
                />
              </label>
              <div className="configuration-row">
                <label>
                  Tipo de valor
                  <select
                    className="configuration-input"
                    value={parameterForm.valueType}
                    onChange={(event) => setParameterForm((current) => ({ ...current, valueType: event.target.value as ConfigurationParameterType }))}
                  >
                    <option value="string">Cadena</option>
                    <option value="integer">Entero</option>
                    <option value="decimal">Decimal</option>
                    <option value="boolean">Booleano</option>
                    <option value="json">JSON</option>
                  </select>
                </label>
                <label className="configuration-checkbox">
                  <input
                    type="checkbox"
                    checked={parameterForm.isSensitive}
                    onChange={(event) => setParameterForm((current) => ({ ...current, isSensitive: event.target.checked }))}
                  />
                  Sensible
                </label>
              </div>
              <label>
                Valor
                <textarea
                  className="configuration-textarea"
                  value={parameterForm.value}
                  onChange={(event) => setParameterForm((current) => ({ ...current, value: event.target.value }))}
                  rows={parameterForm.valueType === "json" ? 4 : 2}
                  placeholder={parameterForm.valueType === "json" ? "{\n  \"clave\": \"valor\"\n}" : ""}
                />
              </label>
              <div className="configuration-row">
                <label>
                  Categoría
                  <input
                    className="configuration-input"
                    value={parameterForm.category}
                    onChange={(event) => setParameterForm((current) => ({ ...current, category: event.target.value }))}
                  />
                </label>
                <label>
                  Descripción
                  <input
                    className="configuration-input"
                    value={parameterForm.description}
                    onChange={(event) => setParameterForm((current) => ({ ...current, description: event.target.value }))}
                  />
                </label>
              </div>
              <label>
                Metadatos (JSON)
                <textarea
                  className="configuration-textarea"
                  value={parameterForm.metadata}
                  onChange={(event) => setParameterForm((current) => ({ ...current, metadata: event.target.value }))}
                  rows={3}
                />
              </label>
              <label>
                Motivo corporativo
                <input
                  className="configuration-input"
                  value={parameterReason}
                  onChange={(event) => setParameterReason(event.target.value)}
                  required
                />
              </label>
              <div className="configuration-actions">
                <Button type="submit" variant="primary" disabled={parameterMutation.isLoading}>
                  {parameterMutation.isLoading ? "Guardando…" : editingParameter ? "Actualizar parámetro" : "Registrar parámetro"}
                </Button>
                {editingParameter ? (
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => {
                      setEditingParameter(null);
                      setParameterForm(emptyParameterForm);
                    }}
                  >
                    Cancelar
                  </Button>
                ) : null}
              </div>
            </fieldset>
          </form>

          <div className="configuration-table-container" role="region" aria-live="polite">
            {loading ? (
              <p className="configuration-empty">Cargando parámetros…</p>
            ) : parameters.length === 0 ? (
              <p className="configuration-empty">No hay parámetros registrados.</p>
            ) : (
              <table className="configuration-table">
                <thead>
                  <tr>
                    <th>Clave</th>
                    <th>Tipo</th>
                    <th>Valor</th>
                    <th>Estado</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {parameters.map((parameter) => (
                    <tr key={parameter.id}>
                      <td>{parameter.key}</td>
                      <td>{parameter.value_type}</td>
                      <td>
                        <code className="configuration-code">{stringifyParameterValue(parameter)}</code>
                      </td>
                      <td>
                        <span className={parameter.is_active ? "status-pill tone-info" : "status-pill tone-warning"}>
                          {parameter.is_active ? "Activo" : "Inactivo"}
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="configuration-link"
                          onClick={() => {
                            setEditingParameter(parameter);
                            setParameterForm({
                              key: parameter.key,
                              name: parameter.name,
                              valueType: parameter.value_type,
                              value: stringifyParameterValue(parameter),
                              category: parameter.category ?? "",
                              description: parameter.description ?? "",
                              metadata: formatMetadata(parameter.metadata),
                              isSensitive: parameter.is_sensitive,
                            });
                          }}
                        >
                          Editar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
