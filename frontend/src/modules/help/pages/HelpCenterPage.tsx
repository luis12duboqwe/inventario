import { useMemo } from "react";
import { useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import Loader from "../../../shared/components/Loader";
import PageHeader from "../../../shared/components/ui/PageHeader";
import { fetchDemoPreview, fetchHelpContext, type HelpGuide } from "../../../services/api/help";

function resolveContextModule(pathname: string, fromState?: string | null): string {
  if (fromState && fromState.startsWith("/dashboard/")) {
    const stateModule = fromState.replace("/dashboard/", "").split("/")[0];
    if (stateModule) {
      return stateModule;
    }
  }

  if (pathname.startsWith("/dashboard/")) {
    const slug = pathname.replace("/dashboard/", "").split("/")[0];
    if (slug) {
      return slug;
    }
  }

  return "inventory";
}

function HelpCenterPage() {
  const location = useLocation();
  const fromState = (location.state as { from?: string } | null)?.from ?? null;
  const currentModule = resolveContextModule(location.pathname, fromState);

  const { data: helpData, isLoading } = useQuery({
    queryKey: ["help", "context"],
    queryFn: fetchHelpContext,
  });

  const { data: demoData } = useQuery({
    queryKey: ["help", "demo"],
    queryFn: fetchDemoPreview,
  });

  const contextualGuide: HelpGuide | undefined = useMemo(() => {
    if (!helpData?.guides) {
      return undefined;
    }
    return helpData.guides.find((guide) => guide.module === currentModule) ?? helpData.guides[0];
  }, [currentModule, helpData?.guides]);

  return (
    <section className="help-center">
      <PageHeader
        title="Centro de ayuda"
        description="Guías contextuales, manuales PDF y modo demostración con datos ficticios."
      />

      {isLoading ? (
        <Loader message="Cargando guías y manuales…" />
      ) : (
        <div className="help-center__grid">
          <article className="card help-center__panel" aria-live="polite">
            <header className="card__header">
              <p className="eyebrow">Guía contextual</p>
              <h2>{contextualGuide?.title ?? "Selecciona un módulo"}</h2>
              <p className="muted">{contextualGuide?.summary}</p>
            </header>
            {contextualGuide ? (
              <>
                <ol className="help-center__steps">
                  {contextualGuide.steps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>
                <div className="help-center__links">
                  <a className="link" href={contextualGuide.manual} download>
                    Descargar manual PDF
                  </a>
                  <a className="link" href={contextualGuide.video} download>
                    Guion de video
                  </a>
                </div>
              </>
            ) : (
              <p className="muted">No hay guías disponibles en este momento.</p>
            )}
          </article>

          <article className="card help-center__panel">
            <header className="card__header">
              <p className="eyebrow">Recursos completos</p>
              <h2>Manual y video por módulo</h2>
              <p className="muted">
                Accede a todos los manuales PDF y guiones de video almacenados en docs/capacitacion para capacitación offline.
              </p>
            </header>
            <div className="help-center__manuals">
              {helpData?.guides.map((guide) => (
                <div key={guide.module} className="help-center__manual">
                  <div>
                    <p className="eyebrow">{guide.module}</p>
                    <h3>{guide.title}</h3>
                    <p className="muted">{guide.summary}</p>
                  </div>
                  <div className="help-center__links">
                    <a className="link" href={guide.manual} download>
                      Manual PDF
                    </a>
                    <a className="link" href={guide.video} download>
                      Video / guion
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </article>

          <article className="card help-center__panel">
            <header className="card__header">
              <p className="eyebrow">Modo demostración</p>
              <h2>Datos ficticios aislados</h2>
              <p className="muted">Explora flujos sin tocar la base corporativa utilizando el dataset simulado.</p>
            </header>
            <div className="help-center__demo">
              <p className={`chip ${demoData?.enabled ? "chip--success" : "chip--muted"}`}>
                {demoData?.enabled ? "Activo" : "Inactivo"}
              </p>
              <p className="muted">{demoData?.notice}</p>
              {demoData?.enabled && demoData.dataset ? (
                <div className="help-center__demo-grid" role="list">
                  <div className="help-center__demo-card" role="listitem">
                    <h4>Inventario simulado</h4>
                    <p className="muted">{demoData.dataset.inventory.length} items listos para pruebas.</p>
                  </div>
                  <div className="help-center__demo-card" role="listitem">
                    <h4>Operaciones de referencia</h4>
                    <p className="muted">{demoData.dataset.operations.length} flujos preservan el motivo corporativo.</p>
                  </div>
                  <div className="help-center__demo-card" role="listitem">
                    <h4>Contactos</h4>
                    <p className="muted">{demoData.dataset.contacts.length} clientes/proveedores ficticios.</p>
                  </div>
                </div>
              ) : null}
            </div>
          </article>
        </div>
      )}
    </section>
  );
}

export default HelpCenterPage;
