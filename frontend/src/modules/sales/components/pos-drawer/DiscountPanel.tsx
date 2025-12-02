import React from "react";

export type POSDiscountPanelProps = {
  valuePct?: number;
  valueAbs?: number;
  onPatch: (patch: { valuePct?: number; valueAbs?: number }) => void;
};

function DiscountPanel({ valuePct, valueAbs, onPatch }: POSDiscountPanelProps) {
  return (
    <div className="pos-discount-panel">
      <div className="pos-discount-field">
        <span className="pos-discount-label">Descuento %</span>
        <input
          type="number"
          min={0}
          value={valuePct ?? 0}
          onChange={(event) => onPatch({ valuePct: Number(event.target.value || 0) })}
          className="pos-discount-input"
        />
      </div>
      <div className="pos-discount-field">
        <span className="pos-discount-label">Descuento $</span>
        <input
          type="number"
          min={0}
          value={valueAbs ?? 0}
          onChange={(event) => onPatch({ valueAbs: Number(event.target.value || 0) })}
          className="pos-discount-input"
        />
      </div>
    </div>
  );
}

export default DiscountPanel;
