import React, { useMemo, useState } from "react";

type CreditNoteLine = {
  id: string;
  name: string;
  qty: number;
  price: number;
  amount: number;
};

type CreditNotePayload = {
  orderId?: string;
  lines: CreditNoteLine[];
  total: number;
  reason: string;
};

type CreditNoteModalProps = {
  open?: boolean;
  orderId?: string;
  onClose?: () => void;
  onSubmit?: (payload: CreditNotePayload) => void;
};

const currency = new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" });

function CreditNoteModal({ open, orderId, onClose, onSubmit }: CreditNoteModalProps) {
  const [lines, setLines] = useState<CreditNoteLine[]>([]);
  const [reason, setReason] = useState<string>("");

  // Sin setState en efectos: limpiar mediante handlers.

  const handleAddLine = () => {
    setLines((prev) => [
      ...prev,
      {
        id: `cn-line-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        name: "",
        qty: 1,
        price: 0,
        amount: 0,
      },
    ]);
  };

  const handleLineChange = (id: string, patch: Partial<CreditNoteLine>) => {
    setLines((prev) =>
      prev.map((line) =>
        line.id === id
          ? {
              ...line,
              ...patch,
              qty: Math.max(0, patch.qty ?? line.qty),
              price: Math.max(0, patch.price ?? line.price),
              amount: Math.max(0, patch.amount ?? line.amount),
            }
          : line,
      ),
    );
  };

  const handleRemoveLine = (id: string) => {
    setLines((prev) => prev.filter((line) => line.id !== id));
  };

  const total = useMemo(() => lines.reduce((sum, line) => sum + (line.amount ?? 0), 0), [lines]);

  const isValid = useMemo(
    () =>
      lines.length > 0 &&
      lines.every((line) => line.qty > 0 && line.amount >= 0) &&
      reason.trim().length >= 5,
    [lines, reason],
  );

  const handleSubmit = () => {
    if (!isValid) {
      return;
    }
    const payload: CreditNotePayload = {
      lines,
      total,
      reason: reason.trim(),
    };
    if (orderId) {
      payload.orderId = orderId;
    }
    onSubmit?.(payload);
    // Reset para próximo uso y cierre
    setLines([]);
    setReason("");
    onClose?.();
  };

  if (!open) {
    return null;
  }

  return (
    <div className="credit-note-modal-overlay">
      <div className="credit-note-modal-content">
        <h3 className="credit-note-modal-title">
          Nota de crédito {orderId ? `(#${orderId})` : ""}
        </h3>
        <div className="credit-note-modal-form">
          {lines.map((line) => (
            <div key={line.id} className="credit-note-modal-line">
              <input
                placeholder="Descripción"
                value={line.name}
                onChange={(event) => handleLineChange(line.id, { name: event.target.value })}
                className="credit-note-modal-input"
              />
              <input
                type="number"
                min={0}
                step="0.01"
                placeholder="Cant"
                value={line.qty}
                onChange={(event) => handleLineChange(line.id, { qty: Number(event.target.value) })}
                className="credit-note-modal-input"
              />
              <input
                type="number"
                min={0}
                step="0.01"
                placeholder="Precio"
                value={line.price}
                onChange={(event) =>
                  handleLineChange(line.id, { price: Number(event.target.value) })
                }
                className="credit-note-modal-input"
              />
              <input
                type="number"
                min={0}
                step="0.01"
                placeholder="Monto"
                value={line.amount}
                onChange={(event) =>
                  handleLineChange(line.id, { amount: Number(event.target.value) })
                }
                className="credit-note-modal-input"
              />
              <button
                onClick={() => handleRemoveLine(line.id)}
                className="credit-note-modal-remove-btn"
              >
                ×
              </button>
            </div>
          ))}
          <button onClick={handleAddLine} className="credit-note-modal-add-btn">
            Agregar línea
          </button>
          <label className="refund-modal-label">
            <span>Motivo corporativo (mín. 5 caracteres)</span>
            <textarea
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              className="credit-note-modal-textarea"
              placeholder="Describe el motivo corporativo de la nota"
            />
          </label>
          <div className="credit-note-modal-total">
            Total NC: {currency.format(Math.max(0, total))}
          </div>
        </div>
        <div className="credit-note-modal-actions">
          <button
            onClick={() => {
              setLines([]);
              setReason("");
              onClose?.();
            }}
            className="credit-note-modal-btn-cancel"
          >
            Cancelar
          </button>
          <button
            type="button"
            disabled={!isValid}
            onClick={handleSubmit}
            className={`credit-note-modal-btn-submit ${
              isValid
                ? "credit-note-modal-btn-submit-valid"
                : "credit-note-modal-btn-submit-invalid"
            }`}
          >
            Emitir NC
          </button>
        </div>
      </div>
    </div>
  );
}

export type { CreditNoteLine, CreditNoteModalProps, CreditNotePayload };
export default CreditNoteModal;
