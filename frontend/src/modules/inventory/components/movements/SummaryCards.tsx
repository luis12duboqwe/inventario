import React from "react";

type Card = { label: string; value: string | number; hint?: string };
type Props = { items?: Card[] };

export default function SummaryCards({ items }: Props) {
  const data = Array.isArray(items) ? items : [];
  return (
    <div className="grid grid-cols-4 gap-3 min-w-[160px]">
      {data.map((c, i) => (
        <div key={i} className="p-3 rounded-xl bg-surface border border-border">
          <div className="text-xs text-muted-foreground">{c.label}</div>
          <div className="text-xl">{c.value}</div>
          {c.hint ? <div className="text-[11px] text-muted-foreground/80">{c.hint}</div> : null}
        </div>
      ))}
    </div>
  );
}
