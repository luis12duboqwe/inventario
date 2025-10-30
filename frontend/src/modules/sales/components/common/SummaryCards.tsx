import React from "react";

type Card = { label: string; value: string | number; hint?: string };

export default function SummaryCards({ items }: { items: Card[] }) {
  const data = Array.isArray(items) ? items : [];
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
        gap: 10,
      }}
    >
      {data.map((card, index) => (
        <div
          key={index}
          style={{
            padding: 12,
            borderRadius: 12,
            border: "1px solid rgba(255,255,255,0.08)",
            background: "rgba(255,255,255,0.02)",
          }}
        >
          <div style={{ fontSize: 12, color: "#94a3b8" }}>{card.label}</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>{card.value}</div>
          {!!card.hint && (
            <div style={{ fontSize: 12, color: "#9ca3af" }}>{card.hint}</div>
          )}
        </div>
      ))}
    </div>
  );
}
