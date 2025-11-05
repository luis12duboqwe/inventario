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

const formatCurrency = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

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
    const payload: PaymentModalPayload = {
      orderId,
      method,
      amount: method === "MIXED" ? cashAmount + cardAmount : amount,
      cashAmount: method === "MIXED" ? cashAmount : undefined,
      cardAmount: method === "MIXED" ? cardAmount : undefined,
      reference: reference.trim() || undefined,
      reason: reason.trim(),
    };
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

  const handleAmountChange = (setter: (value: number) => void) => (event: React.ChangeEvent<HTMLInputElement>) => {
    const next = Number(event.target.value);
    setter(Number.isNaN(next) ? 0 : Math.max(0, next));
  };

  if (!open) {
    return null;
  }

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(8, 15, 35, 0.7)", display: "grid", placeItems: "center", zIndex: 50 }}>
      <div style={{ width: 520, background: "#0b1220", borderRadius: 12, border: "1px solid rgba(56, 189, 248, 0.2)", padding: 16 }}>
        <h3 style={{ marginTop: 0 }}>Registrar cobro {orderId ? `(#${orderId})` : ""}</h3>
        <div style={{ display: "grid", gap: 12 }}>
          <PaymentMethodSelector method={method} onChange={setMethod} />
          {method === "MIXED" ? (
            <>
              <label style={{ display: "grid", gap: 4 }}>
                <span>Efectivo</span>
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  value={cashAmount}
                  onChange={handleAmountChange(setCashAmount)}
                  style={{ width: "100%", padding: 8, borderRadius: 8 }}
                />
              </label>
              <label style={{ display: "grid", gap: 4 }}>
                <span>Tarjeta</span>
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  value={cardAmount}
                  onChange={handleAmountChange(setCardAmount)}
                  style={{ width: "100%", padding: 8, borderRadius: 8 }}
                />
              </label>
            </>
          ) : (
            <label style={{ display: "grid", gap: 4 }}>
              <span>Monto</span>
              <input
                type="number"
                min={0}
                step="0.01"
                value={amount}
                onChange={handleAmountChange(setAmount)}
                style={{ width: "100%", padding: 8, borderRadius: 8 }}
              />
            </label>
          )}
          <label style={{ display: "grid", gap: 4 }}>
            <span>Referencia</span>
            <input
              value={reference}
              onChange={(event) => setReference(event.target.value)}
              style={{ width: "100%", padding: 8, borderRadius: 8 }}
            />
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Motivo corporativo (mín. 5 caracteres)</span>
            <textarea
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              style={{ width: "100%", padding: 8, borderRadius: 8, minHeight: 72 }}
              placeholder="Describe el motivo corporativo"
            />
          </label>
          <div style={{ textAlign: "right", fontSize: 14, color: "#38bdf8" }}>
            Total a registrar: {formatCurrency.format(Math.max(0, totalDisplayed))}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
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
            style={{ padding: "8px 12px", borderRadius: 8 }}
          >
            Cancelar
          </button>
          <button
            type="button"
            disabled={!isValid}
            onClick={handleSubmit}
            style={{
              padding: "8px 12px",
              borderRadius: 8,
              background: isValid ? "#22c55e" : "rgba(34, 197, 94, 0.35)",
              color: isValid ? "#0b1220" : "#1e3a34",
              border: 0,
              cursor: isValid ? "pointer" : "not-allowed",
            }}
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
