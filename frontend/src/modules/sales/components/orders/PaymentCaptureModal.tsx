import React, { useState } from "react";

type Props = {
  open?: boolean;
  onClose?: () => void;
  onSubmit?: (payload: { amount: number }) => void;
};

function PaymentCaptureModal({ open, onClose, onSubmit }: Props) {
  const [paid, setPaid] = useState<string>("");

  if (!open) {
    return null;
  }

  const numericAmount = paid ? Number(paid) : NaN;
  const valid = Number.isFinite(numericAmount) && numericAmount >= 0;

  return (
    <div className="orders-payment-modal-overlay">
      <div className="orders-payment-modal-content">
        <h3 className="orders-payment-modal-title">Registrar pago</h3>
        <input
          type="number"
          placeholder="Monto"
          value={paid}
          onChange={(event) => setPaid(event.target.value)}
          className="orders-payment-modal-input"
        />
        <div className="orders-payment-modal-actions">
          <button onClick={onClose} className="orders-payment-modal-btn">
            Cancelar
          </button>
          <button
            disabled={!valid}
            onClick={() =>
              valid && onSubmit?.({ amount: Number.parseFloat(numericAmount.toFixed(2)) })
            }
            className="orders-payment-modal-btn orders-payment-modal-btn--save"
          >
            Guardar
          </button>
        </div>
      </div>
    </div>
  );
}

export default PaymentCaptureModal;
