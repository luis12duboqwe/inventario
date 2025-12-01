import React, { useState } from "react";

type Props = {
  open?: boolean;
  price: number;
  onClose?: () => void;
  onSubmit?: (newPrice: number) => void;
};

export default function PriceOverrideModal({ open, price, onClose, onSubmit }: Props) {
  const [value, setValue] = useState<number>(price);

  if (!open) {
    return null;
  }

  const valid = Number.isFinite(value) && value >= 0;

  return (
    <div className="pos-price-override-modal-overlay">
      <div className="pos-price-override-modal">
        <h3 className="pos-price-override-modal-title">Modificar precio</h3>
        <input
          type="number"
          value={value}
          onChange={(event) => setValue(Number(event.target.value ?? 0))}
          className="pos-price-override-input"
        />
        <div className="pos-price-override-actions">
          <button onClick={onClose} className="pos-price-override-cancel-btn">
            Cancelar
          </button>
          <button
            disabled={!valid}
            onClick={() => onSubmit?.(value)}
            className="pos-price-override-confirm-btn"
          >
            Aceptar
          </button>
        </div>
      </div>
    </div>
  );
}
