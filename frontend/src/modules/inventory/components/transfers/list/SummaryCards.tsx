import type { ReactNode } from "react";

type SummaryItem = {
  label: string;
  value: ReactNode;
  status?: "default" | "in-progress" | "success" | "danger";
};

type Props = {
  items?: SummaryItem[];
  loading?: boolean;
};

const statusClass: Record<NonNullable<SummaryItem["status"]>, string> = {
  default: "",
  "in-progress": "summary-card--warning",
  success: "summary-card--positive",
  danger: "summary-card--danger",
};

function SummaryCards({ items, loading }: Props) {
  const list = Array.isArray(items) ? items : [];

  return (
    <section className="summary-cards">
      {loading ? (
        <div className="summary-card skeleton" aria-busy>
          Calculando métricas…
        </div>
      ) : (
        list.map((item) => (
          <article key={item.label} className={`summary-card ${statusClass[item.status ?? "default"]}`}>
            <header>{item.label}</header>
            <strong>{item.value}</strong>
          </article>
        ))
      )}
    </section>
  );
}

export type { SummaryItem as TransferSummaryItem };
export default SummaryCards;
