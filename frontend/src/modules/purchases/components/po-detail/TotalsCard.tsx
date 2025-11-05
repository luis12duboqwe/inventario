import React from "react";

type Props = {
  subtotal: number;
  discount: number;
  tax: number;
  total: number;
};

function Row({ label, value, strong }: { label: string; value: number; strong?: boolean }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", fontWeight: strong ? 700 : 400 }}>
      <span style={{ color: strong ? "#e5e7eb" : "#94a3b8" }}>{label}</span>
      <span>{Intl.NumberFormat().format(value || 0)}</span>
    </div>
  );
}

export default function TotalsCard({ subtotal, discount, tax, total }: Props) {

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
      <Row label="Subtotal" value={subtotal} />
      <Row label="Descuento" value={-Math.abs(discount)} />
      <Row label="Impuestos" value={tax} />
      <Row label="Total" value={total} strong />
    </div>
  );
}
