import React from "react";

type Props = {
  qty: number;
};

export default function StockBadge({ qty }: Props) {
  const background = qty <= 0 ? "#b91c1c" : qty < 5 ? "#f59e0b" : "#2563eb";

  return (
    <span
      style={{
        padding: "2px 8px",
        borderRadius: 999,
        background,
        color: "#0b1220",
        fontSize: 12,
        fontWeight: 700,
      }}
    >
      {qty}
    </span>
  );
}
