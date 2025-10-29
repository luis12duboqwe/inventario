import React from "react";

export type PaymentStatusBadgeProps = {
  value: "UNPAID" | "PARTIAL" | "PAID" | "REFUNDED" | string;
};

const PAYMENT_COLORS: Record<string, string> = {
  UNPAID: "#b91c1c",
  PARTIAL: "#f59e0b",
  PAID: "#22c55e",
  REFUNDED: "#64748b",
};

function PaymentStatusBadge({ value }: PaymentStatusBadgeProps) {
  const background = PAYMENT_COLORS[value] ?? "#6b7280";

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: 999,
        background,
        color: "#0b1220",
        fontSize: 12,
        fontWeight: 700,
        textTransform: "uppercase",
      }}
    >
      {value}
    </span>
  );
}

export default PaymentStatusBadge;
