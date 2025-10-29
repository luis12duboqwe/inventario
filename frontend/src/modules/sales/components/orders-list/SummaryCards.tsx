import React from "react";

export type SummaryCard = {
  label: string;
  value: string | number;
  hint?: string;
};

export type SummaryCardsProps = {
  items?: SummaryCard[];
};

function SummaryCards({ items }: SummaryCardsProps) {
  const data = Array.isArray(items) ? items : [];

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
        gap: 12,
      }}
    >
      {data.map((card, index) => (
        <div
          key={`${card.label}-${index}`}
          style={{
            padding: 12,
            borderRadius: 12,
            background: "rgba(255, 255, 255, 0.04)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            display: "grid",
            gap: 4,
          }}
        >
          <span style={{ fontSize: 12, color: "#94a3b8" }}>{card.label}</span>
          <strong style={{ fontSize: 22 }}>{card.value}</strong>
          {card.hint ? <span style={{ fontSize: 11, color: "#64748b" }}>{card.hint}</span> : null}
        </div>
      ))}
    </div>
  );
}

export default SummaryCards;
