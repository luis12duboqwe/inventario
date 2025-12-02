import React from "react";

export type OrderTotalsCardProps = {
  subtotal: number;
  discount: number;
  taxes: number;
  total: number;
  paid: number;
  balance: number;
};

const currency = new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" });

type TotalsRowProps = {
  label: string;
  value: number;
  strong?: boolean;
};

function TotalsRow({ label, value, strong }: TotalsRowProps) {
  return (
    <div
      className={`order-totals-row ${
        strong ? "order-totals-row-strong" : "order-totals-row-normal"
      }`}
    >
      <span className={strong ? "order-totals-label-strong" : "order-totals-label-normal"}>
        {label}
      </span>
      <span>{currency.format(value ?? 0)}</span>
    </div>
  );
}

function TotalsCard({ subtotal, discount, taxes, total, paid, balance }: OrderTotalsCardProps) {
  return (
    <div className="order-totals-card">
      <TotalsRow label="Subtotal" value={subtotal} />
      <TotalsRow label="Descuento" value={discount} />
      <TotalsRow label="Impuestos" value={taxes} />
      <TotalsRow label="Total" value={total} strong />
      <TotalsRow label="Pagado" value={paid} />
      <TotalsRow label="Saldo" value={balance} strong />
    </div>
  );
}

export default TotalsCard;
