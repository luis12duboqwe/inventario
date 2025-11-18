import React from "react";

export type POSChangeDueProps = {
  total: number;
  cash: number;
};

const currency = new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" });

function ChangeDue({ total, cash }: POSChangeDueProps) {
  const change = Math.max(0, (cash ?? 0) - (total ?? 0));

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(2, 1fr)",
        gap: 4,
        padding: 8,
        borderRadius: 8,
        border: "1px solid rgba(255, 255, 255, 0.08)",
      }}
    >
      <span>Total</span>
      <span style={{ textAlign: "right" }}>{currency.format(total ?? 0)}</span>
      <span>Efectivo</span>
      <span style={{ textAlign: "right" }}>{currency.format(cash ?? 0)}</span>
      <strong>Cambio</strong>
      <strong style={{ textAlign: "right" }}>{currency.format(change)}</strong>
    </div>
  );
}

export default ChangeDue;
