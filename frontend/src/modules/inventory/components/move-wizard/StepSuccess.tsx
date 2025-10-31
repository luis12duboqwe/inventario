import React from "react";

type Props = {
  number?: string;
  onOpen?: () => void;
};

export default function StepSuccess({ number, onOpen }: Props) {
  return (
    <div
      style={{
        display: "grid",
        placeItems: "center",
        gap: 8,
        padding: 24,
        borderRadius: 12,
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      <h3 style={{ margin: 0 }}>¡Movimiento creado!</h3>
      <div>Número: {number || "—"}</div>
      <button onClick={onOpen} style={{ padding: "8px 12px", borderRadius: 8 }} type="button">
        Abrir detalle
      </button>
    </div>
  );
}
