import React, { useMemo } from "react";

type SettlementCardProps = {
  total: number;
  paid: number;
};

const currency = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

function SettlementCard({ total, paid }: SettlementCardProps) {
  const balance = useMemo(() => Math.max((total ?? 0) - (paid ?? 0), 0), [paid, total]);

  return (
    <div style={{ padding: 16, borderRadius: 12, background: "rgba(15, 23, 42, 0.75)", border: "1px solid rgba(56, 189, 248, 0.2)", display: "grid", gap: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
        <span>Total</span>
        <span>{currency.format(total ?? 0)}</span>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
        <span>Pagado</span>
        <span>{currency.format(paid ?? 0)}</span>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 700, fontSize: 14 }}>
        <span>Saldo</span>
        <span>{currency.format(balance)}</span>
      </div>
    </div>
  );
}

export type { SettlementCardProps };
export default SettlementCard;
