import { useMemo, useState, useEffect } from "react";
import type React from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { Loader } from "@components/ui/Loader";
import PageHeader from "@components/ui/PageHeader";
import {
  fetchFeedbackMetrics,
  submitFeedback,
  type FeedbackCategory,
  type FeedbackMetrics,
  type FeedbackPayload,
  type FeedbackPriority,
  type FeedbackResponse,
} from "@api/support";

const moduleOptions = [
  { value: "inventory", label: "Inventario" },
  { value: "operations", label: "Operaciones" },
  { value: "pos", label: "POS" },
  { value: "sales", label: "Ventas" },
  { value: "purchases", label: "Compras" },
  { value: "analytics", label: "Analítica" },
  { value: "reports", label: "Reportes" },
  { value: "security", label: "Seguridad" },
  { value: "sync", label: "Sincronización" },
  { value: "help", label: "Ayuda" },
];

const categoryOptions: { value: FeedbackCategory; label: string }[] = [
  { value: "incidente", label: "Incidente" },
  { value: "mejora", label: "Mejora" },
  { value: "usabilidad", label: "Usabilidad" },
  { value: "rendimiento", label: "Rendimiento" },
  { value: "consulta", label: "Consulta" },
];

const priorityOptions: { value: FeedbackPriority; label: string }[] = [
  { value: "baja", label: "Baja" },
  { value: "media", label: "Media" },
  { value: "alta", label: "Alta" },
  { value: "critica", label: "Crítica" },
];

function formatRelative(date: string) {
  const parsed = new Date(date);
  return parsed.toLocaleString("es-ES", { dateStyle: "medium", timeStyle: "short" });
}

function buildUsageContext(): Record<string, unknown> {
  if (typeof window === "undefined") {
    return {};
  }
  return {
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    language: navigator.language,
    path: window.location.pathname,
    user_agent: navigator.userAgent,
  };
}

function FeedbackPage() {
  const [payload, setPayload] = useState<FeedbackPayload>({
    module: "inventory",
    category: "incidente",
    priority: "media",
    title: "",
    description: "",
    contact: "",
  });
  const [impact, setImpact] = useState("");
  const [steps, setSteps] = useState("");
  const [tracking, setTracking] = useState<FeedbackResponse | null>(null);
  const usageContext = useMemo(() => buildUsageContext(), []);

  const {
    data: metrics,
    isLoading: loadingMetrics,
    refetch,
  } = useQuery<FeedbackMetrics>({
    queryKey: ["support", "metrics"],
    queryFn: fetchFeedbackMetrics,
  });

  const feedbackMutation = useMutation({
    mutationFn: submitFeedback,
    onSuccess: (data) => {
      setTracking(data);
      refetch();
    },
  });

  useEffect(() => {
    if (!tracking) {
      return;
    }
    const timeoutId = window.setTimeout(() => setTracking(null), 9000);
    return () => window.clearTimeout(timeoutId);
  }, [tracking]);

  const handleChange =
    (field: keyof FeedbackPayload) =>
    (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      setPayload((prev) => ({ ...prev, [field]: event.target.value }));
    };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const metadata: Record<string, unknown> = {
      impacto: impact || undefined,
      pasos: steps || undefined,
    };
    await feedbackMutation.mutateAsync({
      ...payload,
      metadata,
      usage_context: usageContext,
    });
    setPayload((prev) => ({ ...prev, title: "", description: "" }));
    setImpact("");
    setSteps("");
  };

  const pending = feedbackMutation.isPending;

  return (
    <section className="support-feedback">
      <PageHeader
        title="Sugerencias y soporte"
        description="Envía incidencias o ideas clasificadas y consulta prioridades basadas en uso real."
      />

      <div className="support-feedback__grid">
        <form className="card support-feedback__form" onSubmit={handleSubmit}>
          <header className="card__header">
            <p className="eyebrow">Clasificación y seguimiento</p>
            <h2>Registrar nuevo feedback</h2>
            <p className="muted">
              Describe el módulo, impacto y pasos. Usamos estas señales y las métricas de uso para
              priorizar mejoras.
            </p>
          </header>

          <div className="form-grid">
            <label className="form-control">
              <span>Módulo</span>
              <select value={payload.module} onChange={handleChange("module")}>
                {moduleOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="form-control">
              <span>Categoría</span>
              <select value={payload.category} onChange={handleChange("category") as never}>
                {categoryOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="form-control">
              <span>Prioridad</span>
              <select value={payload.priority} onChange={handleChange("priority") as never}>
                {priorityOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="form-control">
              <span>Contacto (opcional)</span>
              <input
                type="email"
                placeholder="correo@softmobile.test"
                value={payload.contact ?? ""}
                onChange={handleChange("contact")}
              />
            </label>
          </div>

          <label className="form-control">
            <span>Título</span>
            <input
              required
              type="text"
              placeholder="Ej. El POS tarda en abrir"
              value={payload.title}
              onChange={handleChange("title")}
            />
          </label>

          <label className="form-control">
            <span>Descripción</span>
            <textarea
              required
              rows={4}
              placeholder="Explica lo que sucede, el resultado esperado y los datos probados."
              value={payload.description}
              onChange={handleChange("description")}
            />
          </label>

          <div className="form-grid">
            <label className="form-control">
              <span>Impacto en la operación</span>
              <textarea
                rows={3}
                placeholder="Ej. Retraso en aperturas de turno y colas de clientes"
                value={impact}
                onChange={(event) => setImpact(event.target.value)}
              />
            </label>
            <label className="form-control">
              <span>Pasos para reproducir</span>
              <textarea
                rows={3}
                placeholder="1. Abrir POS → 2. Seleccionar tienda Norte → 3. Esperar carga"
                value={steps}
                onChange={(event) => setSteps(event.target.value)}
              />
            </label>
          </div>

          <div className="support-feedback__actions">
            <button className="btn btn--primary" type="submit" disabled={pending}>
              {pending ? "Enviando…" : "Enviar feedback"}
            </button>
            <p className="muted">
              Incluimos zona horaria, idioma y ruta navegada para acelerar la reproducción
              controlada.
            </p>
          </div>

          {tracking && (
            <div className="support-feedback__alert" role="status" aria-live="polite">
              <strong>Seguimiento listo:</strong> código {tracking.tracking_id} — estado{" "}
              {tracking.status}.
            </div>
          )}
        </form>

        <aside className="card support-feedback__panel" aria-live="polite">
          <header className="card__header">
            <p className="eyebrow">Métricas recientes</p>
            <h2>Cómo priorizamos</h2>
            <p className="muted">
              Calculamos un puntaje combinando prioridad reportada, estado y uso real de cada
              módulo.
            </p>
          </header>

          {loadingMetrics ? (
            <Loader message="Calculando métricas de soporte…" />
          ) : (
            <div className="support-feedback__stats">
              <div className="stat-card">
                <p className="eyebrow">Totales</p>
                <strong>{metrics?.totals.feedback ?? 0}</strong>
                <span className="muted">Registros en la última ventana</span>
              </div>
              <div className="stat-card">
                <p className="eyebrow">Abiertos</p>
                <strong>{metrics?.by_status?.abierto ?? 0}</strong>
                <span className="muted">Pendientes de seguimiento</span>
              </div>
              <div className="stat-card">
                <p className="eyebrow">Críticos</p>
                <strong>{metrics?.by_priority?.critica ?? 0}</strong>
                <span className="muted">Reportes con mayor urgencia</span>
              </div>
              <div className="stat-card">
                <p className="eyebrow">Consultas</p>
                <strong>{metrics?.by_category?.consulta ?? 0}</strong>
                <span className="muted">Preguntas e ideas registradas</span>
              </div>
            </div>
          )}
        </aside>
      </div>

      <div className="support-feedback__grid">
        <article className="card support-feedback__panel">
          <header className="card__header">
            <p className="eyebrow">Prioridades sugeridas</p>
            <h2>Hotspots por uso</h2>
            <p className="muted">
              Multiplicamos urgencia y actividad para resaltar mejoras con mayor impacto.
            </p>
          </header>
          {loadingMetrics ? (
            <Loader message="Cargando hotspots…" />
          ) : metrics?.hotspots?.length ? (
            <ul className="support-feedback__list">
              {metrics.hotspots.map((hotspot) => (
                <li key={hotspot.module}>
                  <div>
                    <p className="eyebrow">{hotspot.module}</p>
                    <strong>{hotspot.priority_score.toFixed(2)}</strong>
                    <p className="muted">
                      {hotspot.open_feedback} abiertos · {hotspot.interactions_last_30d}{" "}
                      interacciones / 30 días
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">Aún no hay suficientes datos para priorizar módulos.</p>
          )}
        </article>

        <article className="card support-feedback__panel">
          <header className="card__header">
            <p className="eyebrow">Seguimiento</p>
            <h2>Últimos registros</h2>
            <p className="muted">
              Toma nota del código de seguimiento para dar continuidad con soporte.
            </p>
          </header>
          {loadingMetrics ? (
            <Loader message="Leyendo feedback reciente…" />
          ) : metrics?.recent_feedback?.length ? (
            <ul className="support-feedback__list">
              {metrics.recent_feedback.map((item) => (
                <li key={item.tracking_id}>
                  <div>
                    <p className="eyebrow">
                      {item.module} · {item.category}
                    </p>
                    <strong>{item.title}</strong>
                    <p className="muted">
                      Estado: {item.status} · {formatRelative(item.created_at)}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">Envía el primer registro para habilitar el historial.</p>
          )}
        </article>
      </div>
    </section>
  );
}

export default FeedbackPage;
