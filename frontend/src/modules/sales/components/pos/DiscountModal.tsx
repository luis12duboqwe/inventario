import React, { useState } from "react";

type Payload = {
  type: "PERCENT" | "AMOUNT";
  value: number;
};

type Props = {
  open?: boolean;
  onClose?: () => void;
  onSubmit?: (payload: Payload) => void;
};

export default function DiscountModal({ open, onClose, onSubmit }: Props) {
  const [type, setType] = useState<"PERCENT" | "AMOUNT">("PERCENT");
  const [value, setValue] = useState<number>(0);

  if (!open) {
    return null;
  }

  const valid = Number.isFinite(value) && value >= 0 && (type === "PERCENT" ? value <= 100 : true);

  return (
    <div className="pos-modal-overlay">
      <div className="pos-modal-content">
        <h3 className="pos-modal-title">Descuento en línea</h3>
        <select
          value={type}
          onChange={(event) => setType(event.target.value as "PERCENT" | "AMOUNT")}
          className="pos-modal-select"
        >
          <option value="PERCENT">% Porcentaje</option>
          <option value="AMOUNT">Monto fijo</option>
        </select>
        <input
          type="number"
          value={value}
          onChange={(event) => setValue(Number(event.target.value ?? 0))}
          className="pos-modal-input"
        />
        <div className="pos-modal-actions">
          <button onClick={onClose} className="pos-modal-cancel-btn">
            Cancelar
          </button>
          <button
            disabled={!valid}
            onClick={() => onSubmit?.({ type, value })}
            className="pos-modal-apply-btn"
          >
            Aplicar
          </button>
        </div>
      </div>
    </div>
  );
}
