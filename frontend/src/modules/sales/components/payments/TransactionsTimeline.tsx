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

const currency = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });
const dateFormatter = new Intl.DateTimeFormat("es-MX", { dateStyle: "medium", timeStyle: "short" });

function TransactionsTimeline({ items }: TransactionsTimelineProps) {
  const entries = Array.isArray(items) ? items : [];

  return (
    <div style={{ padding: 16, borderRadius: 12, background: "rgba(15, 23, 42, 0.75)", border: "1px solid rgba(148, 163, 184, 0.2)", display: "grid", gap: 12 }}>
      <div style={{ fontSize: 12, color: "#94a3b8", textTransform: "uppercase" }}>Transacciones</div>
      {entries.length === 0 ? (
        <div style={{ color: "#9ca3af", fontSize: 13 }}>Sin movimientos</div>
      ) : (
        <div style={{ display: "grid", gap: 12 }}>
          {entries.map((entry) => (
            <div key={entry.id} style={{ display: "grid", gap: 4 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <span>{dateFormatter.format(new Date(entry.date))}</span>
                {typeof entry.amount === "number" ? <span>{currency.format(entry.amount)}</span> : null}
              </div>
              <div style={{ fontSize: 13, color: "#e2e8f0" }}>
                <span
                  style={{
                    display: "inline-block",
                    marginRight: 8,
                    padding: "2px 8px",
                    borderRadius: 999,
                    fontSize: 11,
                    background:
                      entry.kind === "PAY"
                        ? "rgba(34, 197, 94, 0.25)"
                        : entry.kind === "REFUND"
                        ? "rgba(239, 68, 68, 0.25)"
                        : "rgba(37, 99, 235, 0.25)",
                    color: entry.kind === "REFUND" ? "#fca5a5" : entry.kind === "CN" ? "#bfdbfe" : "#bbf7d0",
                  }}
                >
                  {entry.kind === "PAY" ? "Cobro" : entry.kind === "REFUND" ? "Reembolso" : "Nota crédito"}
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
