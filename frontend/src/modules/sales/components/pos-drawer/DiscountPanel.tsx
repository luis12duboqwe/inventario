import React from "react";

export type POSDiscountPanelProps = {
  valuePct?: number;
  valueAbs?: number;
  onPatch: (patch: { valuePct?: number; valueAbs?: number }) => void;
};

function DiscountPanel({ valuePct, valueAbs, onPatch }: POSDiscountPanelProps) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 8 }}>
      <div style={{ display: "grid", gap: 4 }}>
        <span style={{ fontSize: 12, color: "#94a3b8" }}>Descuento %</span>
        <input
          type="number"
          min={0}
          value={valuePct ?? 0}
          onChange={(event) => onPatch({ valuePct: Number(event.target.value || 0) })}
          style={{ padding: 8, borderRadius: 8 }}
        />
      </div>
      <div style={{ display: "grid", gap: 4 }}>
        <span style={{ fontSize: 12, color: "#94a3b8" }}>Descuento $</span>
        <input
          type="number"
          min={0}
          value={valueAbs ?? 0}
          onChange={(event) => onPatch({ valueAbs: Number(event.target.value || 0) })}
          style={{ padding: 8, borderRadius: 8 }}
        />
      </div>
    </div>
  );
}

export default DiscountPanel;
