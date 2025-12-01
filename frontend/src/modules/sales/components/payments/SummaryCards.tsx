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
      <div className="payments-summary-cards">
        {Array.from({ length: Math.max(items.length, 4) }).map((_, index) => (
          <div key={index} className="payments-summary-card-skeleton" />
        ))}
      </div>
    );
  }

  return (
    <div className="payments-summary-cards">
      {items.map((item) => (
        <div key={item.label} className="payments-summary-card">
          <span className="payments-summary-card-label">{item.label}</span>
          <span className="payments-summary-card-value">{item.value}</span>
          {item.helperText ? (
            <span className="payments-summary-card-helper">{item.helperText}</span>
          ) : null}
        </div>
      ))}
    </div>
  );
}

export type { PaymentsSummaryCardsProps, SummaryCardItem };
export default PaymentsSummaryCards;
