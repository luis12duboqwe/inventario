import React from "react";

type SummaryItem = {
  label: string;
  value: string | number;
  hint?: string;
};

type Props = {
  items?: SummaryItem[];
};

const wrapperStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(4, minmax(160px, 1fr))",
  gap: 12,
};

const cardStyle: React.CSSProperties = {
  padding: 12,
  borderRadius: 12,
  background: "rgba(255, 255, 255, 0.04)",
  border: "1px solid rgba(255, 255, 255, 0.08)",
  display: "grid",
  gap: 4,
};

export default function SummaryCards({ items }: Props) {
  const data = Array.isArray(items) ? items : [];
  return (
    <div style={wrapperStyle}>
      {data.map((card, index) => (
        <div key={index} style={cardStyle}>
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
