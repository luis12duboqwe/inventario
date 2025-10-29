import React from "react";

type CustomerDebtCardProps = {
  totalDebt?: number;
  creditLimit?: number;
};

const currency = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

function CustomerDebtCard({ totalDebt = 0, creditLimit }: CustomerDebtCardProps) {
  const hasLimit = typeof creditLimit === "number" && !Number.isNaN(creditLimit);
  const available = hasLimit ? Math.max(creditLimit - totalDebt, 0) : undefined;

  return (
    <div style={{ padding: 16, borderRadius: 12, background: "rgba(15, 23, 42, 0.75)", border: "1px solid rgba(100, 116, 139, 0.35)", display: "grid", gap: 6 }}>
      <div style={{ fontSize: 12, color: "#94a3b8", textTransform: "uppercase" }}>Deuda consolidada</div>
      <div style={{ fontWeight: 700, fontSize: 22 }}>{currency.format(Math.max(totalDebt, 0))}</div>
      {hasLimit ? (
        <div style={{ fontSize: 12, color: "#38bdf8" }}>Disponible: {currency.format(available ?? 0)}</div>
      ) : null}
    </div>
  );
}

export type { CustomerDebtCardProps };
export default CustomerDebtCard;
