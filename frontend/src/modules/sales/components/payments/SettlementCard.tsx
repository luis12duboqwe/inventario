import React, { useMemo } from "react";

type SettlementCardProps = {
  total: number;
  paid: number;
};

const currency = new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" });

function SettlementCard({ total, paid }: SettlementCardProps) {
  const balance = useMemo(() => Math.max((total ?? 0) - (paid ?? 0), 0), [paid, total]);

  return (
    <div className="settlement-card">
      <div className="settlement-card-row">
        <span>Total</span>
        <span>{currency.format(total ?? 0)}</span>
      </div>
      <div className="settlement-card-row">
        <span>Pagado</span>
        <span>{currency.format(paid ?? 0)}</span>
      </div>
      <div className="settlement-card-row-bold">
        <span>Saldo</span>
        <span>{currency.format(balance)}</span>
      </div>
    </div>
  );
}

export type { SettlementCardProps };
export default SettlementCard;
