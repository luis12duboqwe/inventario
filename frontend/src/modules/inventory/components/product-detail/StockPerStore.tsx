import React from "react";

type Row = {
  store: string;
  qty: number;
};

type Props = {
  items?: Row[];
};

export default function StockPerStore({ items }: Props) {
  const data = Array.isArray(items) ? items : [];

  if (data.length === 0) {
    return <div className="text-muted-foreground">Sin datos</div>;
  }

  return (
    <div className="grid gap-2">
      {data.map((row, index) => (
        <div key={`${row.store}-${index}`} className="flex justify-between">
          <span>{row.store}</span>
          <span>{row.qty}</span>
        </div>
      ))}
    </div>
  );
}
