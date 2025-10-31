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
    return <div style={{ color: "#9ca3af" }}>Sin datos</div>;
  }

  return (
    <div style={{ display: "grid", gap: 6 }}>
      {data.map((row, index) => (
        <div key={`${row.store}-${index}`} style={{ display: "flex", justifyContent: "space-between" }}>
          <span>{row.store}</span>
          <span>{row.qty}</span>
        </div>
      ))}
    </div>
  );
}
