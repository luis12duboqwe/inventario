import React from "react";

type Card = {
  label: string;
  value: string | number;
  hint?: string;
};

type Props = {
  items?: Card[];
};

function SummaryCards({ items }: Props) {
  const data = Array.isArray(items) ? items : [];
  return (
    <div className="orders-summary-cards">
      {data.map((card, index) => (
        <div key={`order-summary-${index}`} className="orders-summary-card">
          <div className="orders-summary-card-label">{card.label}</div>
          <div className="orders-summary-card-value">{card.value}</div>
          {card.hint ? <div className="orders-summary-card-hint">{card.hint}</div> : null}
        </div>
      ))}
    </div>
  );
}

export default SummaryCards;
