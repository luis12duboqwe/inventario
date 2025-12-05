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
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {data.map((card, index) => (
        <div
          key={`${card.label}-${index}`}
          className="p-4 rounded-xl bg-surface-highlight border border-border"
        >
          <div className="text-xs text-muted-foreground mb-1">{card.label}</div>
          <div className="text-2xl font-semibold">{card.value}</div>
          {card.hint ? <div className="text-xs text-muted-foreground mt-1">{card.hint}</div> : null}
        </div>
      ))}
    </div>
  );
}
