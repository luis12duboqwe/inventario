import React from "react";

type Payment = {
  id: string;
  date: string;
  amount: number;
  method: string;
  note?: string;
};

type Props = {
  items?: Payment[];
};

export default function PaymentsTimeline({ items }: Props) {
  const data = Array.isArray(items) ? items : [];

  return (
    <div
      style={{
        padding: 12,
        borderRadius: 12,
        background: "rgba(255, 255, 255, 0.04)",
        border: "1px solid rgba(255, 255, 255, 0.08)",
      }}
    >
      <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 8 }}>Pagos</div>
      {data.length === 0 ? (
        <div style={{ color: "#9ca3af" }}>Sin pagos</div>
      ) : (
        <div style={{ display: "grid", gap: 8 }}>
          {data.map((payment) => (
            <div key={payment.id} style={{ display: "flex", justifyContent: "space-between" }}>
              <span>
                {new Date(payment.date).toLocaleString()} — {payment.method}
              </span>
              <span>{Intl.NumberFormat().format(payment.amount)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
