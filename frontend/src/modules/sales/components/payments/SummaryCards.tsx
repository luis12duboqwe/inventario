import React from "react";

type SummaryCardItem = {
  label: string;
  value: string;
  helperText?: string;
};

type PaymentsSummaryCardsProps = {
  items: SummaryCardItem[];
  loading?: boolean;
};

function PaymentsSummaryCards({ items, loading }: PaymentsSummaryCardsProps) {
  if (loading) {
    return (
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 12,
        }}
      >
        {Array.from({ length: Math.max(items.length, 4) }).map((_, index) => (
          <div
            key={index}
            style={{
              padding: 16,
              borderRadius: 12,
              background: "rgba(255, 255, 255, 0.04)",
              border: "1px solid rgba(148, 163, 184, 0.2)",
              minHeight: 88,
            }}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
        gap: 12,
      }}
    >
      {items.map((item) => (
        <div
          key={item.label}
          style={{
            padding: 16,
            borderRadius: 12,
            background: "linear-gradient(135deg, rgba(15, 23, 42, 0.9), rgba(30, 64, 175, 0.35))",
            border: "1px solid rgba(56, 189, 248, 0.25)",
            display: "grid",
            gap: 4,
          }}
        >
          <span style={{ fontSize: 12, color: "#94a3b8", textTransform: "uppercase" }}>{item.label}</span>
          <span style={{ fontSize: 24, fontWeight: 700 }}>{item.value}</span>
          {item.helperText ? (
            <span style={{ fontSize: 12, color: "#38bdf8" }}>{item.helperText}</span>
          ) : null}
        </div>
      ))}
    </div>
  );
}

export type { PaymentsSummaryCardsProps, SummaryCardItem };
export default PaymentsSummaryCards;
