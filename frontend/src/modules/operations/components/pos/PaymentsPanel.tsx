import { FormEvent, useMemo, useState } from "react";

export type PaymentLine = {
  id: string;
  method: string;
  amount: number;
};

type PaymentsPanelProps = {
  payments: PaymentLine[];
  onAdd: (payment: Omit<PaymentLine, "id">) => void;
  onUpdate: (id: string, update: Partial<PaymentLine>) => void;
  onRemove: (id: string) => void;
  totalDue: number;
};

const PAYMENT_METHODS = ["EFECTIVO", "TARJETA", "TRANSFERENCIA", "CREDITO"];

// [PACK34-UI]
export default function PaymentsPanel({ payments, onAdd, onUpdate, onRemove, totalDue }: PaymentsPanelProps) {
  const [draft, setDraft] = useState<Omit<PaymentLine, "id">>({ method: "EFECTIVO", amount: totalDue });

  const pendingAmount = useMemo(() => {
    const registered = payments.reduce((acc, entry) => acc + entry.amount, 0);
    return Math.max(totalDue - registered, 0);
  }, [payments, totalDue]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (draft.amount <= 0) {
      return;
    }
    onAdd(draft);
    setDraft({ method: draft.method, amount: pendingAmount });
  };

  return (
    <section className="card">
      <header className="card__header">
        <h3 className="card__title">Pagos</h3>
        <p className="card__subtitle">Divide el pago por método para registrar arqueos y conciliaciones.</p>
      </header>

      <form className="pos-payments-form" onSubmit={handleSubmit}>
        <label>
          <span>Método</span>
          <select
            value={draft.method}
            onChange={(event) => setDraft((prev) => ({ ...prev, method: event.target.value }))}
          >
            {PAYMENT_METHODS.map((method) => (
              <option key={method} value={method}>
                {method}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Monto</span>
          <input
            type="number"
            min={0}
            step="0.01"
            value={draft.amount}
            onChange={(event) =>
              setDraft((prev) => ({ ...prev, amount: Number(event.target.value) || 0 }))
            }
          />
        </label>
        <button type="submit" className="btn btn--primary">
          Añadir pago
        </button>
      </form>

      <div className="pos-payments-summary">
        <span>Total por cobrar:</span>
        <strong>${totalDue.toFixed(2)}</strong>
      </div>
      <div className="pos-payments-summary">
        <span>Pendiente por registrar:</span>
        <strong>${pendingAmount.toFixed(2)}</strong>
      </div>

      <ul className="pos-payments-list">
        {payments.length === 0 ? (
          <li className="muted-text">Sin pagos capturados.</li>
        ) : (
          payments.map((payment) => (
            <li key={payment.id} className="pos-payments-list__item">
              <div>
                <select
                  value={payment.method}
                  onChange={(event) => onUpdate(payment.id, { method: event.target.value })}
                >
                  {PAYMENT_METHODS.map((method) => (
                    <option key={method} value={method}>
                      {method}
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  value={payment.amount}
                  onChange={(event) =>
                    onUpdate(payment.id, { amount: Number(event.target.value) || 0 })
                  }
                />
              </div>
              <button type="button" className="btn btn--ghost" onClick={() => onRemove(payment.id)}>
                Eliminar
              </button>
            </li>
          ))
        )}
      </ul>
    </section>
  );
}

