import React from "react";

type Props = {
  subtotal: number;
  taxes: number;
  total: number;
  receivedValue?: number;
};

const cardStyle: React.CSSProperties = {
  padding: 12,
  borderRadius: 12,
  background: "rgba(255, 255, 255, 0.04)",
  border: "1px solid rgba(255, 255, 255, 0.08)",
  display: "grid",
  gap: 8,
};

const rowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
};

export default function TotalsCard({ subtotal, taxes, total, receivedValue }: Props) {
  const Row = ({ label, value, strong }: { label: string; value: number; strong?: boolean }) => (
    <div style={{ ...rowStyle, fontWeight: strong ? 700 : 400 }}>
      <span style={{ color: strong ? "#e5e7eb" : "#94a3b8" }}>{label}</span>
      <span>{Intl.NumberFormat().format(value || 0)}</span>
    </div>
  );

  return (
    <div style={cardStyle}>
      <Row label="Subtotal" value={subtotal} />
      <Row label="Impuestos" value={taxes} />
      <Row label="Total" value={total} strong />
      {typeof receivedValue === "number" ? <Row label="Valor recibido" value={receivedValue} /> : null}
    </div>
  );
}
