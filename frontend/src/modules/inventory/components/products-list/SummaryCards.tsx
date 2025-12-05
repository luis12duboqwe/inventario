import React from "react";
import "../../InventoryTable.css"; // Ensure styles are loaded

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
    <div className="summary-cards-grid">
      {data.map((card, index) => (
        <div key={index} className="summary-card">
          <div className="summary-card__label">{card.label}</div>
          <div className="summary-card__value">{card.value}</div>
          {card.hint ? <div className="summary-card__hint">{card.hint}</div> : null}
        </div>
      ))}
    </div>
  );
}
