import React, { useMemo, useState } from "react";

type RefundModalPayload = {
  orderId?: string;
  amount: number;
  method: "CASH" | "CARD" | "TRANSFER";
  reason: "DEFECT" | "CUSTOMER_CHANGE" | "PRICE_ADJUST" | "OTHER";
  notes?: string;
};

type RefundModalProps = {
  open?: boolean;
  orderId?: string;
  onClose?: () => void;
  onSubmit?: (payload: RefundModalPayload) => void;
};

function RefundModal({ open, orderId, onClose, onSubmit }: RefundModalProps) {
  const [amount, setAmount] = useState<number>(0);
  const [method, setMethod] = useState<"CASH" | "CARD" | "TRANSFER">("CASH");
  const [reason, setReason] = useState<"DEFECT" | "CUSTOMER_CHANGE" | "PRICE_ADJUST" | "OTHER">(
    "OTHER",
  );
  const [notes, setNotes] = useState<string>("");

  // Sin setState en efectos: limpiar en handlers.

  const isValid = useMemo(() => amount > 0 && notes.trim().length >= 5, [amount, notes]);

  const handleSubmit = () => {
    if (!isValid) {
      return;
    }
    const payload: RefundModalPayload = {
      amount,
      method,
      reason,
    };
    const trimmedNotes = notes.trim();
    if (trimmedNotes) {
      payload.notes = trimmedNotes;
    }
    if (orderId) {
      payload.orderId = orderId;
    }
    onSubmit?.(payload);
    // reset para un nuevo ciclo y cerrar el modal
    setAmount(0);
    setMethod("CASH");
    setReason("OTHER");
    setNotes("");
    onClose?.();
  };

  const handleAmountChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const next = Number(event.target.value);
    setAmount(Number.isNaN(next) ? 0 : Math.max(0, next));
  };

  if (!open) {
    return null;
  }

  return (
    <div className="refund-modal-overlay">
      <div className="refund-modal-content">
        <h3 className="refund-modal-title">Reembolso {orderId ? `(#${orderId})` : ""}</h3>
        <div className="refund-modal-form">
          <label className="refund-modal-label">
            <span>Monto</span>
            <input
              type="number"
              min={0}
              step="0.01"
              value={amount}
              onChange={handleAmountChange}
              className="refund-modal-input"
            />
          </label>
          <label className="refund-modal-label">
            <span>Método</span>
            <select
              value={method}
              onChange={(event) => setMethod(event.target.value as typeof method)}
              className="refund-modal-input"
            >
              <option value="CASH">Efectivo</option>
              <option value="CARD">Tarjeta</option>
              <option value="TRANSFER">Transferencia</option>
            </select>
          </label>
          <label className="refund-modal-label">
            <span>Motivo</span>
            <select
              value={reason}
              onChange={(event) => setReason(event.target.value as typeof reason)}
              className="refund-modal-input"
            >
              <option value="DEFECT">Defecto</option>
              <option value="CUSTOMER_CHANGE">Cambio de opinión</option>
              <option value="PRICE_ADJUST">Ajuste de precio</option>
              <option value="OTHER">Otro</option>
            </select>
          </label>
          <label className="refund-modal-label">
            <span>Motivo corporativo (mín. 5 caracteres)</span>
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              className="refund-modal-textarea"
              placeholder="Describe el motivo corporativo"
            />
          </label>
        </div>
        <div className="refund-modal-actions">
          <button
            onClick={() => {
              setAmount(0);
              setMethod("CASH");
              setReason("OTHER");
              setNotes("");
              onClose?.();
            }}
            className="refund-modal-btn-cancel"
          >
            Cancelar
          </button>
          <button
            type="button"
            disabled={!isValid}
            onClick={handleSubmit}
            className={`refund-modal-btn-submit ${
              isValid ? "refund-modal-btn-submit-valid" : "refund-modal-btn-submit-invalid"
            }`}
          >
            Reembolsar
          </button>
        </div>
      </div>
    </div>
  );
}

export type { RefundModalPayload, RefundModalProps };
export default RefundModal;
