import React from "react";

type TimelineEntry = {
  id: string;
  kind: "PAY" | "REFUND" | "CN";
  message: string;
  date: string;
  amount?: number;
};

type TransactionsTimelineProps = {
  items?: TimelineEntry[];
};

const currency = new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" });
const dateFormatter = new Intl.DateTimeFormat("es-HN", { dateStyle: "medium", timeStyle: "short" });

function TransactionsTimeline({ items }: TransactionsTimelineProps) {
  const entries = Array.isArray(items) ? items : [];

  const getBadgeClass = (kind: string) => {
    switch (kind) {
      case "PAY":
        return "transactions-timeline-badge--pay";
      case "REFUND":
        return "transactions-timeline-badge--refund";
      case "CN":
        return "transactions-timeline-badge--cn";
      default:
        return "";
    }
  };

  return (
    <div className="transactions-timeline">
      <div className="transactions-timeline-header">Transacciones</div>
      {entries.length === 0 ? (
        <div className="transactions-timeline-empty">Sin movimientos</div>
      ) : (
        <div className="transactions-timeline-list">
          {entries.map((entry) => (
            <div key={entry.id} className="transactions-timeline-entry">
              <div className="transactions-timeline-entry-header">
                <span>{dateFormatter.format(new Date(entry.date))}</span>
                {typeof entry.amount === "number" ? (
                  <span>{currency.format(entry.amount)}</span>
                ) : null}
              </div>
              <div className="transactions-timeline-entry-body">
                <span className={`transactions-timeline-badge ${getBadgeClass(entry.kind)}`}>
                  {entry.kind === "PAY"
                    ? "Cobro"
                    : entry.kind === "REFUND"
                    ? "Reembolso"
                    : "Nota crédito"}
                </span>
                {entry.message}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export type { TimelineEntry, TransactionsTimelineProps };
export default TransactionsTimeline;
