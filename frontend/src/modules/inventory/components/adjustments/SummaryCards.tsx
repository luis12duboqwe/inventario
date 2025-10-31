import type { ReactNode } from "react";

export type SummaryCardItem = {
  label: string;
  value: ReactNode;
  description?: ReactNode;
  tone?: "default" | "positive" | "warning" | "danger";
};

type Props = {
  items?: SummaryCardItem[];
  loading?: boolean;
};

const toneClass: Record<NonNullable<SummaryCardItem["tone"]>, string> = {
  default: "",
  positive: "summary-card--positive",
  warning: "summary-card--warning",
  danger: "summary-card--danger",
};

function SummaryCards({ items, loading }: Props) {
  const data = Array.isArray(items) ? items : [];

  return (
    <section className="summary-cards">
      {loading ? (
        <div className="summary-card skeleton" aria-busy>
          Cargando métricas…
        </div>
      ) : (
        data.map((item) => {
          const tone = item.tone ?? "default";
          return (
            <article key={item.label} className={`summary-card ${toneClass[tone]}`}>
              <header>{item.label}</header>
              <strong>{item.value}</strong>
              {item.description ? <p>{item.description}</p> : null}
            </article>
          );
        })
      )}
    </section>
  );
}

export default SummaryCards;
