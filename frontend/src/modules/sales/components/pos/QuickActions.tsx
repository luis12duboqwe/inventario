import React from "react";

type Props = {
  onToggleHold?: () => void;
  onOpenPayments?: () => void;
  onClearCart?: () => void;
  onFocusSearch?: () => void;
};

export default function QuickActions({ onToggleHold, onOpenPayments, onClearCart, onFocusSearch }: Props) {
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      <button onClick={onFocusSearch} style={{ padding: "8px 12px", borderRadius: 8 }}>
        F1 Buscar
      </button>
      <button
        onClick={onOpenPayments}
        style={{ padding: "8px 12px", borderRadius: 8, background: "#22c55e", color: "#0b1220", border: 0, fontWeight: 700 }}
      >
        F2 Cobrar
      </button>
      <button
        onClick={onToggleHold}
        style={{ padding: "8px 12px", borderRadius: 8, background: "rgba(255,255,255,0.08)", color: "#e5e7eb", border: 0 }}
      >
        F3 En espera
      </button>
      <button onClick={onClearCart} style={{ padding: "8px 12px", borderRadius: 8 }}>
        F4 Limpiar
      </button>
    </div>
  );
}
