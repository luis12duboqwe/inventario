import React from "react";

type CustomerDebtCardProps = {
  totalDebt?: number;
  creditLimit?: number;
};

const currency = new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" });

function CustomerDebtCard({ totalDebt = 0, creditLimit }: CustomerDebtCardProps) {
  const hasLimit = typeof creditLimit === "number" && !Number.isNaN(creditLimit);
  const available = hasLimit ? Math.max(creditLimit - totalDebt, 0) : undefined;

  return (
    <div className="customer-debt-card">
      <div className="customer-debt-card-label">Deuda consolidada</div>
      <div className="customer-debt-card-value">{currency.format(Math.max(totalDebt, 0))}</div>
      {hasLimit ? (
        <div className="customer-debt-card-available">
          Disponible: {currency.format(available ?? 0)}
        </div>
      ) : null}
    </div>
  );
}

export type { CustomerDebtCardProps };
export default CustomerDebtCard;
