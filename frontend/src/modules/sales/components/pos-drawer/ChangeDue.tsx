import React from "react";

export type POSChangeDueProps = {
  total: number;
  cash: number;
};

const currency = new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" });

function ChangeDue({ total, cash }: POSChangeDueProps) {
  const change = Math.max(0, (cash ?? 0) - (total ?? 0));

  return (
    <div className="pos-change-due">
      <span>Total</span>
      <span className="pos-change-due-value">{currency.format(total ?? 0)}</span>
      <span>Efectivo</span>
      <span className="pos-change-due-value">{currency.format(cash ?? 0)}</span>
      <strong>Cambio</strong>
      <strong className="pos-change-due-total">{currency.format(change)}</strong>
    </div>
  );
}

export default ChangeDue;
