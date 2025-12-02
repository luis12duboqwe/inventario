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
    <div className="orders-list-summary-cards">
      {data.map((card, index) => (
        <div key={`${card.label}-${index}`} className="orders-list-summary-card">
          <span className="orders-list-summary-card__label">{card.label}</span>
          <strong className="orders-list-summary-card__value">{card.value}</strong>
          {card.hint ? <span className="orders-list-summary-card__hint">{card.hint}</span> : null}
        </div>
      ))}
    </div>
  );
}

export default SummaryCards;
