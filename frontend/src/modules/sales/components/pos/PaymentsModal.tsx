import React, { useState } from "react";

type Payment = {
  id: string;
  type: "CASH" | "CARD" | "TRANSFER" | "OTHER";
  amount: number;
  ref?: string;
};

type Props = {
  open?: boolean;
  total: number;
  onClose?: () => void;
  onSubmit?: (payments: Payment[]) => void;
};

export default function PaymentsModal({ open, total, onClose, onSubmit }: Props) {
  const [payments, setPayments] = useState<Payment[]>([
    { id: "1", type: "CASH", amount: total, ref: "" },
  ]);

  if (!open) {
    return null;
  }

  const addPayment = () => {
    setPayments((prev) => [
      ...prev,
      { id: String(Date.now()), type: "CASH", amount: 0, ref: "" },
    ]);
  };

  const updatePayment = (id: string, payload: Partial<Payment>) => {
    setPayments((prev) =>
      prev.map((payment) => (payment.id === id ? { ...payment, ...payload } : payment)),
    );
  };

  const removePayment = (id: string) => {
    setPayments((prev) => prev.filter((payment) => payment.id !== id));
  };

  const paidAmount = payments.reduce((acc, payment) => acc + (payment.amount ?? 0), 0);
  const valid = paidAmount >= total && payments.every((payment) => payment.amount >= 0);

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "grid", placeItems: "center" }}>
      <div
        style={{
          width: 560,
          background: "#0b1220",
          borderRadius: 12,
          border: "1px solid rgba(255,255,255,0.08)",
          padding: 16,
        }}
      >
        <h3 style={{ marginTop: 0 }}>Cobros</h3>
        <div style={{ display: "grid", gap: 8, maxHeight: 360, overflow: "auto" }}>
          {payments.map((payment) => (
            <div
              key={payment.id}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 120px 1fr 28px",
                gap: 8,
                alignItems: "center",
              }}
            >
              <select
                value={payment.type}
                onChange={(event) =>
                  updatePayment(payment.id, {
                    type: event.target.value as Payment["type"],
                  })
                }
                style={{ padding: 8, borderRadius: 8 }}
              >
                <option value="CASH">Efectivo</option>
                <option value="CARD">Tarjeta</option>
                <option value="TRANSFER">Transferencia</option>
                <option value="OTHER">Otro</option>
              </select>
              <input
                type="number"
                value={payment.amount}
                onChange={(event) =>
                  updatePayment(payment.id, { amount: Number(event.target.value ?? 0) })
                }
                style={{ padding: 8, borderRadius: 8 }}
              />
              <input
                placeholder="Ref/last4"
                value={payment.ref ?? ""}
                onChange={(event) => updatePayment(payment.id, { ref: event.target.value })}
                style={{ padding: 8, borderRadius: 8 }}
              />
              <button
                onClick={() => removePayment(payment.id)}
                style={{ padding: "6px 8px", borderRadius: 8 }}
              >
                ×
              </button>
            </div>
          ))}
          <button onClick={addPayment} style={{ padding: "8px 12px", borderRadius: 8 }}>
            Agregar medio
          </button>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8 }}>
          <div>
            Total: <b>{Intl.NumberFormat().format(total)}</b>
          </div>
          <div>
            Pagado: <b>{Intl.NumberFormat().format(paidAmount)}</b>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
          <button onClick={onClose} style={{ padding: "8px 12px", borderRadius: 8 }}>
            Cancelar
          </button>
          <button
            disabled={!valid}
            onClick={() => onSubmit?.(payments)}
            style={{ padding: "8px 12px", borderRadius: 8, background: "#22c55e", color: "#0b1220", border: 0 }}
          >
            Confirmar
          </button>
        </div>
      </div>
    </div>
  );
}
