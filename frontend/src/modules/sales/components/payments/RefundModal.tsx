import React, { useEffect, useMemo, useState } from "react";

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
  const [reason, setReason] = useState<"DEFECT" | "CUSTOMER_CHANGE" | "PRICE_ADJUST" | "OTHER">("OTHER");
  const [notes, setNotes] = useState<string>("");

  useEffect(() => {
    if (!open) {
      setAmount(0);
      setMethod("CASH");
      setReason("OTHER");
      setNotes("");
    }
  }, [open]);

  const isValid = useMemo(() => amount > 0 && notes.trim().length >= 5, [amount, notes]);

  const handleSubmit = () => {
    if (!isValid) {
      return;
    }
    onSubmit?.({
      orderId,
      amount,
      method,
      reason,
      notes: notes.trim() || undefined,
    });
  };

  const handleAmountChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const next = Number(event.target.value);
    setAmount(Number.isNaN(next) ? 0 : Math.max(0, next));
  };

  if (!open) {
    return null;
  }

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(8, 15, 35, 0.7)", display: "grid", placeItems: "center", zIndex: 50 }}>
      <div style={{ width: 520, background: "#0b1220", borderRadius: 12, border: "1px solid rgba(248, 113, 113, 0.3)", padding: 16 }}>
        <h3 style={{ marginTop: 0 }}>Reembolso {orderId ? `(#${orderId})` : ""}</h3>
        <div style={{ display: "grid", gap: 12 }}>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Monto</span>
            <input
              type="number"
              min={0}
              step="0.01"
              value={amount}
              onChange={handleAmountChange}
              style={{ width: "100%", padding: 8, borderRadius: 8 }}
            />
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Método</span>
            <select value={method} onChange={(event) => setMethod(event.target.value as typeof method)} style={{ width: "100%", padding: 8, borderRadius: 8 }}>
              <option value="CASH">Efectivo</option>
              <option value="CARD">Tarjeta</option>
              <option value="TRANSFER">Transferencia</option>
            </select>
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Motivo</span>
            <select value={reason} onChange={(event) => setReason(event.target.value as typeof reason)} style={{ width: "100%", padding: 8, borderRadius: 8 }}>
              <option value="DEFECT">Defecto</option>
              <option value="CUSTOMER_CHANGE">Cambio de opinión</option>
              <option value="PRICE_ADJUST">Ajuste de precio</option>
              <option value="OTHER">Otro</option>
            </select>
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Motivo corporativo (mín. 5 caracteres)</span>
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              style={{ width: "100%", padding: 8, borderRadius: 8, minHeight: 96 }}
              placeholder="Describe el motivo corporativo"
            />
          </label>
        </div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
          <button onClick={onClose} style={{ padding: "8px 12px", borderRadius: 8 }}>Cancelar</button>
          <button
            type="button"
            disabled={!isValid}
            onClick={handleSubmit}
            style={{
              padding: "8px 12px",
              borderRadius: 8,
              background: isValid ? "#ef4444" : "rgba(239, 68, 68, 0.35)",
              color: "#fef2f2",
              border: 0,
              cursor: isValid ? "pointer" : "not-allowed",
            }}
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
