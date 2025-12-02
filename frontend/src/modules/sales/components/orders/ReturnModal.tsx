import React, { useState } from "react";

type Props = {
  open?: boolean;
  onClose?: () => void;
  onSubmit?: (payload: { amount: number }) => void;
};

function ReturnModal({ open, onClose, onSubmit }: Props) {
  const [amount, setAmount] = useState<string>("");

  if (!open) {
    return null;
  }

  const numericAmount = amount ? Number(amount) : NaN;
  const valid = Number.isFinite(numericAmount) && numericAmount >= 0;

  return (
    <div className="orders-return-modal-overlay">
      <div className="orders-return-modal-content">
        <h3 className="orders-return-modal-title">Procesar devolución</h3>
        <input
          type="number"
          placeholder="Monto a devolver"
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
          className="orders-return-modal-input"
        />
        <div className="orders-return-modal-actions">
          <button onClick={onClose} className="orders-return-modal-btn">
            Cancelar
          </button>
          <button
            disabled={!valid}
            onClick={() =>
              valid && onSubmit?.({ amount: Number.parseFloat(numericAmount.toFixed(2)) })
            }
            className="orders-return-modal-btn orders-return-modal-btn--confirm"
          >
            Confirmar
          </button>
        </div>
      </div>
    </div>
  );
}

export default ReturnModal;
