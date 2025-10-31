import React from "react";

type Card = {
  label: string;
  value: string | number;
  hint?: string;
};

type Props = {
  items?: Card[];
};

export default function SummaryCards({ items }: Props) {
  const data = Array.isArray(items) ? items : [];

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, minmax(160px,1fr))",
        gap: 12,
      }}
    >
      {data.map((card, index) => (
        <div
          key={`${card.label}-${index}`}
          style={{
            padding: 12,
            borderRadius: 12,
            background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          <div style={{ fontSize: 12, color: "#9ca3af" }}>{card.label}</div>
          <div style={{ fontSize: 22 }}>{card.value}</div>
          {card.hint ? (
            <div style={{ fontSize: 11, color: "#94a3b8" }}>{card.hint}</div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
