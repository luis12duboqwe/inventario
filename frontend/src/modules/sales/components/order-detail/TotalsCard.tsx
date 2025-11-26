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
    <div style={{ display: "flex", justifyContent: "space-between", fontWeight: strong ? 700 : 400 }}>
      <span style={{ color: strong ? "#e5e7eb" : "#94a3b8" }}>{label}</span>
      <span>{currency.format(value ?? 0)}</span>
    </div>
  );
}

function TotalsCard({ subtotal, discount, taxes, total, paid, balance }: OrderTotalsCardProps) {
  return (
    <div
      style={{
        padding: 12,
        borderRadius: 12,
        background: "rgba(255, 255, 255, 0.04)",
        border: "1px solid rgba(255, 255, 255, 0.08)",
        display: "grid",
        gap: 8,
      }}
    >
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
