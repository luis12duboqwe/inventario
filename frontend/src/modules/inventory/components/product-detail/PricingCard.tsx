import React from "react";

type Props = {
  base: number;
  cost: number;
  margin: number;
};

function Row({ label, value, strong }: { label: string; value: number; strong?: boolean }) {
  return (
    <div className={`flex justify-between ${strong ? "font-bold" : "font-normal"}`}>
      <span className={strong ? "text-foreground" : "text-muted-foreground"}>{label}</span>
      <span>{Intl.NumberFormat().format(value || 0)}</span>
    </div>
  );
}

Row.displayName = "PricingCardRow";

export default function PricingCard({ base, cost, margin }: Props) {
  return (
    <div className="p-3 rounded-xl bg-surface border border-border grid gap-2">
      <Row label="Precio base" value={base} strong />
      <Row label="Costo" value={cost} />
      <Row label="Margen" value={margin} />
    </div>
  );
}
