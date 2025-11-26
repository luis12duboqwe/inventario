import React, { useEffect, useState } from "react";

import type { PaymentType } from "../../../../services/sales";

type Payment = {
  id: string;
  type: PaymentType;
  amount: number;
  reference?: string;
  tipAmount?: number;
  terminalId?: string;
};

type TerminalOption = { id: string; label: string };

type Props = {
  open?: boolean;
  total: number;
  terminals?: TerminalOption[];
  defaultTerminalId?: string;
  tipSuggestions?: number[];
  onClose?: () => void;
  onSubmit?: (payments: Payment[]) => void;
};

export default function PaymentsModal({
  open,
  total,
  terminals,
  defaultTerminalId,
  tipSuggestions,
  onClose,
  onSubmit,
}: Props) {
  const [payments, setPayments] = useState<Payment[]>([]);

  useEffect(() => {
    if (!open) return;
    setPayments((prev) => {
      if (prev.length > 0) {
        return prev;
      }
      return [
        {
          id: "1",
          type: "CASH",
          amount: total,
          terminalId: defaultTerminalId,
        },
      ];
    });
  }, [open, total, defaultTerminalId]);

  if (!open) {
    return null;
  }

  const addPayment = () => {
    setPayments((prev) => [
      ...prev,
      {
        id: String(Date.now()),
        type: "CASH",
        amount: 0,
        terminalId: defaultTerminalId,
      },
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

  const basePaid = payments.reduce((acc, payment) => acc + (payment.amount ?? 0), 0);
  const tipsPaid = payments.reduce((acc, payment) => acc + (payment.tipAmount ?? 0), 0);
  const valid =
    basePaid >= total &&
    payments.every((payment) => (payment.amount ?? 0) >= 0 && (payment.tipAmount ?? 0) >= 0);

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
                  gridTemplateColumns: "1fr 120px 110px 1fr 1fr 28px",
                  gap: 8,
                  alignItems: "center",
                }}
              >
                <select
                  value={payment.type}
                  onChange={(event) =>
                    updatePayment(payment.id, {
                      type: event.target.value as PaymentType,
                      terminalId:
                        event.target.value === "CARD" || event.target.value === "TRANSFER"
                          ? payment.terminalId || defaultTerminalId || terminals?.[0]?.id
                          : undefined,
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
                type="number"
                value={payment.tipAmount ?? 0}
                onChange={(event) =>
                  updatePayment(payment.id, { tipAmount: Number(event.target.value ?? 0) })
                }
                style={{ padding: 8, borderRadius: 8 }}
                placeholder="Propina"
                min={0}
              />
              <div style={{ display: "grid", gap: 4 }}>
                {(payment.type === "CARD" || payment.type === "TRANSFER") ? (
                  <select
                    value={payment.terminalId ?? defaultTerminalId ?? ""}
                    onChange={(event) =>
                      updatePayment(payment.id, { terminalId: event.target.value || undefined })
                    }
                    style={{ padding: 8, borderRadius: 8 }}
                  >
                    <option value="">Terminal</option>
                    {terminals?.map((terminal) => (
                      <option key={terminal.id} value={terminal.id}>
                        {terminal.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <div style={{ fontSize: 12, color: "#64748b" }}>Sin terminal</div>
                )}
                {tipSuggestions && tipSuggestions.length > 0 ? (
                  <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                    {tipSuggestions.map((tip) => (
                      <button
                        key={`${payment.id}-tip-${tip}`}
                        type="button"
                        onClick={() =>
                          updatePayment(payment.id, {
                            tipAmount: Number(((total * tip) / 100).toFixed(2)),
                          })
                        }
                        style={{
                          padding: "4px 6px",
                          borderRadius: 6,
                          border: "1px solid rgba(56,189,248,0.4)",
                          background: "rgba(56,189,248,0.1)",
                          color: "#38bdf8",
                          fontSize: 11,
                        }}
                      >
                        +{tip}%
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
              <input
                placeholder="Ref/last4"
                value={payment.reference ?? ""}
                onChange={(event) => updatePayment(payment.id, { reference: event.target.value })}
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
            Pagado: <b>{Intl.NumberFormat().format(basePaid)}</b>
          </div>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4, fontSize: 12, color: "#94a3b8" }}>
          <div>
            Propinas: <b style={{ color: "#38bdf8" }}>{Intl.NumberFormat().format(tipsPaid)}</b>
          </div>
          <div>
            Total con propina: <b>{Intl.NumberFormat().format(basePaid + tipsPaid)}</b>
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
