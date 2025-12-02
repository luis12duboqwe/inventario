import React, { useMemo, useState } from "react";

import PaymentMethodSelector, { PaymentMethod } from "./PaymentMethodSelector";

type PaymentModalPayload = {
  orderId?: string;
  method: PaymentMethod;
  amount: number;
  cashAmount?: number;
  cardAmount?: number;
  reference?: string;
  reason: string;
};

type PaymentModalProps = {
  open?: boolean;
  orderId?: string;
  onClose?: () => void;
  onSubmit?: (payload: PaymentModalPayload) => void;
};

const formatCurrency = new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" });

function PaymentModal({ open, orderId, onClose, onSubmit }: PaymentModalProps) {
  const [method, setMethod] = useState<PaymentMethod>("CASH");
  const [amount, setAmount] = useState<number>(0);
  const [cashAmount, setCashAmount] = useState<number>(0);
  const [cardAmount, setCardAmount] = useState<number>(0);
  const [reference, setReference] = useState<string>("");
  const [reason, setReason] = useState<string>("");

  // Sin setState en efectos: limpiamos al cancelar o tras confirmar.

  const isValid = useMemo(() => {
    if (method === "MIXED") {
      const totalMixed = (cashAmount ?? 0) + (cardAmount ?? 0);
      return totalMixed > 0 && reason.trim().length >= 5;
    }
    return amount > 0 && reason.trim().length >= 5;
  }, [amount, cardAmount, cashAmount, method, reason]);

  const totalDisplayed = method === "MIXED" ? cashAmount + cardAmount : amount;

  const handleSubmit = () => {
    if (!isValid) {
      return;
    }
    const totalAmount = method === "MIXED" ? cashAmount + cardAmount : amount;
    const payload: PaymentModalPayload = {
      method,
      amount: totalAmount,
      reason: reason.trim(),
    };
    if (method === "MIXED" && cashAmount > 0) {
      payload.cashAmount = cashAmount;
    }
    if (method === "MIXED" && cardAmount > 0) {
      payload.cardAmount = cardAmount;
    }
    const trimmedReference = reference.trim();
    if (trimmedReference) {
      payload.reference = trimmedReference;
    }
    if (orderId) {
      payload.orderId = orderId;
    }
    onSubmit?.(payload);
    // restablecer campos para el próximo uso
    setMethod("CASH");
    setAmount(0);
    setCashAmount(0);
    setCardAmount(0);
    setReference("");
    setReason("");
    onClose?.();
  };

  const handleAmountChange =
    (setter: (value: number) => void) => (event: React.ChangeEvent<HTMLInputElement>) => {
      const next = Number(event.target.value);
      setter(Number.isNaN(next) ? 0 : Math.max(0, next));
    };

  if (!open) {
    return null;
  }

  return (
    <div className="payment-modal-overlay">
      <div className="payment-modal-content">
        <h3 className="payment-modal-title">Registrar cobro {orderId ? `(#${orderId})` : ""}</h3>
        <div className="payment-modal-form">
          <PaymentMethodSelector method={method} onChange={setMethod} />
          {method === "MIXED" ? (
            <>
              <label className="payment-modal-label">
                <span>Efectivo</span>
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  value={cashAmount}
                  onChange={handleAmountChange(setCashAmount)}
                  className="payment-modal-input"
                />
              </label>
              <label className="payment-modal-label">
                <span>Tarjeta</span>
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  value={cardAmount}
                  onChange={handleAmountChange(setCardAmount)}
                  className="payment-modal-input"
                />
              </label>
            </>
          ) : (
            <label className="payment-modal-label">
              <span>Monto</span>
              <input
                type="number"
                min={0}
                step="0.01"
                value={amount}
                onChange={handleAmountChange(setAmount)}
                className="payment-modal-input"
              />
            </label>
          )}
          <label className="payment-modal-label">
            <span>Referencia</span>
            <input
              value={reference}
              onChange={(event) => setReference(event.target.value)}
              className="payment-modal-input"
            />
          </label>
          <label className="payment-modal-label">
            <span>Motivo corporativo (mín. 5 caracteres)</span>
            <textarea
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              className="payment-modal-textarea"
              placeholder="Describe el motivo corporativo"
            />
          </label>
          <div className="payment-modal-total">
            Total a registrar: {formatCurrency.format(Math.max(0, totalDisplayed))}
          </div>
        </div>
        <div className="payment-modal-actions">
          <button
            onClick={() => {
              setMethod("CASH");
              setAmount(0);
              setCashAmount(0);
              setCardAmount(0);
              setReference("");
              setReason("");
              onClose?.();
            }}
            className="payment-modal-btn-cancel"
          >
            Cancelar
          </button>
          <button
            type="button"
            disabled={!isValid}
            onClick={handleSubmit}
            className={`payment-modal-btn-submit ${
              isValid ? "payment-modal-btn-submit-valid" : "payment-modal-btn-submit-invalid"
            }`}
          >
            Registrar
          </button>
        </div>
      </div>
    </div>
  );
}

export type { PaymentModalPayload, PaymentModalProps };
export default PaymentModal;
