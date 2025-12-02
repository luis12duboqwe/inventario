import React, { useEffect, useState } from "react";

import type { PaymentType } from "../../../../services/sales";

type Payment = {
  id: string;
  type: PaymentType;
  amount: number;
  reference?: string;
  tipAmount?: number;
  terminalId?: string | undefined;
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
    <div className="pos-payments-modal-overlay">
      <div className="pos-payments-modal">
        <h3 className="pos-payments-modal-title">Cobros</h3>
        <div className="pos-payments-list">
          {payments.map((payment) => (
            <div key={payment.id} className="pos-payments-item">
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
                className="pos-payments-select"
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
                className="pos-payments-input"
              />
              <input
                type="number"
                value={payment.tipAmount ?? 0}
                onChange={(event) =>
                  updatePayment(payment.id, { tipAmount: Number(event.target.value ?? 0) })
                }
                className="pos-payments-input"
                placeholder="Propina"
                min={0}
              />
              <div className="pos-payments-terminal-container">
                {payment.type === "CARD" || payment.type === "TRANSFER" ? (
                  <select
                    value={payment.terminalId ?? defaultTerminalId ?? ""}
                    onChange={(event) =>
                      updatePayment(payment.id, { terminalId: event.target.value || undefined })
                    }
                    className="pos-payments-select"
                  >
                    <option value="">Terminal</option>
                    {terminals?.map((terminal) => (
                      <option key={terminal.id} value={terminal.id}>
                        {terminal.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="pos-payments-no-terminal">Sin terminal</div>
                )}
                {tipSuggestions && tipSuggestions.length > 0 ? (
                  <div className="pos-payments-tips">
                    {tipSuggestions.map((tip) => (
                      <button
                        key={`${payment.id}-tip-${tip}`}
                        type="button"
                        onClick={() =>
                          updatePayment(payment.id, {
                            tipAmount: Number(((total * tip) / 100).toFixed(2)),
                          })
                        }
                        className="pos-payments-tip-btn"
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
                className="pos-payments-input"
              />
              <button onClick={() => removePayment(payment.id)} className="pos-payments-remove-btn">
                ×
              </button>
            </div>
          ))}
          <button onClick={addPayment} className="pos-payments-add-btn">
            Agregar medio
          </button>
        </div>
        <div className="pos-payments-summary">
          <div>
            Total: <b>{Intl.NumberFormat().format(total)}</b>
          </div>
          <div>
            Pagado: <b>{Intl.NumberFormat().format(basePaid)}</b>
          </div>
        </div>
        <div className="pos-payments-summary-tips">
          <div>
            Propinas:{" "}
            <b className="pos-payments-tip-amount">{Intl.NumberFormat().format(tipsPaid)}</b>
          </div>
          <div>
            Total con propina: <b>{Intl.NumberFormat().format(basePaid + tipsPaid)}</b>
          </div>
        </div>
        <div className="pos-payments-actions">
          <button onClick={onClose} className="pos-payments-cancel-btn">
            Cancelar
          </button>
          <button
            disabled={!valid}
            onClick={() => onSubmit?.(payments)}
            className="pos-payments-confirm-btn"
          >
            Confirmar
          </button>
        </div>
      </div>
    </div>
  );
}
