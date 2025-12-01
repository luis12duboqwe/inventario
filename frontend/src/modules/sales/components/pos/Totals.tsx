import React from "react";

const formatter = new Intl.NumberFormat("es-HN", {
  style: "currency",
  currency: "MXN",
  maximumFractionDigits: 2,
});

type Props = {
  subtotal: number;
  discountTotal: number;
  taxTotal: number;
  grandTotal: number;
  onCharge?: () => void;
  onHold?: () => void;
  onClear?: () => void;
};

function Item({ label, value, strong }: { label: string; value: number; strong?: boolean }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", fontWeight: strong ? 700 : 400 }}>
      <span style={{ color: strong ? "#e5e7eb" : "#94a3b8" }}>{label}</span>
      <span>{formatter.format(value || 0)}</span>
    </div>
  );
}

export default function Totals({ subtotal, discountTotal, taxTotal, grandTotal, onCharge, onHold, onClear }: Props) {
  return (
    <div
      style={{
        display: "grid",
        gap: 8,
        padding: 12,
        borderRadius: 12,
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      <Item label="Subtotal" value={subtotal} />
      <Item label="Descuento" value={-Math.abs(discountTotal)} />
      <Item label="Impuestos" value={taxTotal} />
      <Item label="Total" value={grandTotal} strong />
      <div style={{ display: "flex", gap: 8, marginTop: 8, justifyContent: "flex-end" }}>
        <button onClick={onClear} style={{ padding: "8px 12px", borderRadius: 8 }}>
          Limpiar
        </button>
        <button
          onClick={onHold}
          style={{ padding: "8px 12px", borderRadius: 8, background: "rgba(255,255,255,0.08)", color: "#e5e7eb", border: 0 }}
        >
          En espera
        </button>
        <button
          onClick={onCharge}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#22c55e", color: "#0b1220", border: 0, fontWeight: 700 }}
        >
          Cobrar
        </button>
      </div>
    </div>
  );
}
