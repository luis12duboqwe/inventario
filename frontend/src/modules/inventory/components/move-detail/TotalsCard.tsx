import React from "react";

type Props = {
  subtotal: number;
  adjustments: number;
  total: number;
};

function Row({ label, value, strong }: { label: string; value: number; strong?: boolean }) {
  return (
    <div className={`flex justify-between ${strong ? "font-bold" : "font-normal"}`}>
      <span className={strong ? "text-foreground" : "text-muted-foreground"}>{label}</span>
      <span>{Intl.NumberFormat().format(value || 0)}</span>
    </div>
  );
}

Row.displayName = "MoveTotalsRow";

export default function TotalsCard({ subtotal, adjustments, total }: Props) {
  return (
    <div className="p-3 rounded-xl bg-surface border border-border grid gap-2">
      <Row label="Subtotal" value={subtotal} />
      <Row label="Ajustes" value={adjustments} />
      <Row label="Total" value={total} strong />
    </div>
  );
}
