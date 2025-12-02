import type { ReactNode } from "react";

import Accordion from "@components/ui/Accordion/Accordion";

export type FlowAuditAction = {
  id: string;
  label: string;
  onClick?: () => void;
  tooltip?: string;
};

export type FlowAuditFlow = {
  id: string;
  title: string;
  summary: string;
  steps: string[];
  actions?: FlowAuditAction[];
  footer?: ReactNode;
};

type FlowAuditCardProps = {
  title: string;
  subtitle?: string;
  flows: FlowAuditFlow[];
};

function FlowAuditCard({ title, subtitle, flows }: FlowAuditCardProps) {
  return (
    <section className="card flow-audit-card" aria-label={`Auditoría de flujo: ${title}`}>
      <header className="flow-audit-card__header">
        <div>
          <p className="eyebrow">Auditoría</p>
          <h2>{title}</h2>
          {subtitle ? <p className="card-subtitle">{subtitle}</p> : null}
        </div>
      </header>

      <Accordion
        allowMultiple
        items={flows.map((flow) => ({
          id: flow.id,
          title: flow.title,
          description: flow.summary,
          content: (
            <div className="flow-audit-card__content">
              <ol className="flow-audit-card__steps">
                {flow.steps.map((step, index) => (
                  <li key={`${flow.id}-step-${index + 1}`}>{step}</li>
                ))}
              </ol>
              {flow.actions && flow.actions.length > 0 ? (
                <div
                  className="flow-audit-card__actions"
                  aria-label={`Acciones rápidas para ${flow.title}`}
                >
                  {flow.actions.map((action) => (
                    <button
                      key={action.id}
                      type="button"
                      className="button button--ghost"
                      title={action.tooltip ?? action.label}
                      onClick={action.onClick}
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              ) : null}
              {flow.footer ? <div className="flow-audit-card__footer">{flow.footer}</div> : null}
            </div>
          ),
          defaultOpen: true,
        }))}
      />
    </section>
  );
}

export default FlowAuditCard;
