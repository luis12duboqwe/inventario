import React from "react";

type Card = { label: string; value: string | number; hint?: string };

export default function SummaryCards({ items }: { items: Card[] }) {
  const data = Array.isArray(items) ? items : [];
  return (
    <div className="sales-summary-cards">
      {data.map((card, index) => (
        <div key={index} className="sales-summary-card">
          <div className="sales-summary-card-label">{card.label}</div>
          <div className="sales-summary-card-value">{card.value}</div>
          {!!card.hint && <div className="sales-summary-card-hint">{card.hint}</div>}
        </div>
      ))}
    </div>
  );
}
