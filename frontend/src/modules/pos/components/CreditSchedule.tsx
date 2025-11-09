import { useMemo } from "react";

import type {
  CreditScheduleEntry,
  CustomerDebtSnapshot,
  CustomerPaymentReceipt,
} from "@/api";

type CreditScheduleProps = {
  debtSummary?: CustomerDebtSnapshot | null;
  schedule?: CreditScheduleEntry[];
  debtReceiptBase64?: string | null;
  paymentReceipts?: CustomerPaymentReceipt[];
};

function formatCurrency(value: number): string {
  return value.toLocaleString("es-MX", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleDateString("es-MX", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function downloadPdf(base64: string, filename: string): void {
  const link = document.createElement("a");
  link.href = `data:application/pdf;base64,${base64}`;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

const STATUS_LABELS: Record<CreditScheduleEntry["status"], string> = {
  pending: "Pendiente",
  due_soon: "Próximo a vencer",
  overdue: "Vencido",
};

type ScheduleBucket = {
  key: string;
  title: string;
  entries: CreditScheduleEntry[];
};

function groupSchedule(entries: CreditScheduleEntry[]): ScheduleBucket[] {
  const buckets: Record<string, ScheduleBucket> = {};
  for (const entry of entries) {
    const status = entry.status;
    const bucket = buckets[status] ?? {
      key: status,
      title: STATUS_LABELS[status] ?? status,
      entries: [],
    };
    bucket.entries.push(entry);
    buckets[status] = bucket;
  }
  return Object.values(buckets);
}

export default function CreditSchedule({
  debtSummary,
  schedule = [],
  debtReceiptBase64,
  paymentReceipts = [],
}: CreditScheduleProps) {
  const grouped = useMemo(() => groupSchedule(schedule), [schedule]);

  if (!debtSummary) {
    return null;
  }

  return (
    <section className="credit-schedule" aria-live="polite">
      <header className="credit-schedule__header">
        <h2>Calendario de crédito</h2>
        <p className="credit-schedule__caption">
          Controla abonos y recordatorios para mantener el saldo al día.
        </p>
      </header>
      <dl className="credit-schedule__summary">
        <div>
          <dt>Saldo anterior</dt>
          <dd>${formatCurrency(debtSummary.previous_balance)}</dd>
        </div>
        <div>
          <dt>Nuevo cargo</dt>
          <dd>${formatCurrency(debtSummary.new_charges)}</dd>
        </div>
        <div>
          <dt>Abonos aplicados</dt>
          <dd>${formatCurrency(debtSummary.payments_applied)}</dd>
        </div>
        <div>
          <dt>Saldo pendiente</dt>
          <dd className="credit-schedule__summary-remaining">
            ${formatCurrency(debtSummary.remaining_balance)}
          </dd>
        </div>
      </dl>

      {grouped.length > 0 ? (
        <div className="credit-schedule__list" role="list">
          {grouped.map((bucket) => (
            <article key={bucket.key} className={`credit-schedule__group credit-schedule__group--${bucket.key}`}>
              <h3>{bucket.title}</h3>
              <ul>
                {bucket.entries.map((entry) => (
                  <li key={`${entry.sequence}-${entry.due_date}`} className="credit-schedule__item">
                    <div>
                      <span className="credit-schedule__sequence">#{entry.sequence}</span>
                      <time dateTime={entry.due_date}>{formatDate(entry.due_date)}</time>
                    </div>
                    <div>
                      <span className="credit-schedule__amount">${formatCurrency(entry.amount)}</span>
                      {entry.reminder ? (
                        <span className="credit-schedule__reminder">{entry.reminder}</span>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      ) : (
        <p className="credit-schedule__empty">No hay pagos programados para este crédito.</p>
      )}

      {(debtReceiptBase64 || paymentReceipts.length > 0) ? (
        <div className="credit-schedule__actions">
          {debtReceiptBase64 ? (
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => downloadPdf(debtReceiptBase64, `comprobante-deuda-${Date.now()}.pdf`)}
            >
              Descargar comprobante de deuda
            </button>
          ) : null}
          {paymentReceipts.map((receipt, index) => (
            <button
              key={`payment-receipt-${receipt.ledger_entry.id}`}
              type="button"
              className="btn btn--ghost"
              onClick={() => downloadPdf(
                receipt.receipt_pdf_base64,
                `abono-${receipt.ledger_entry.id}-${index + 1}.pdf`
              )}
            >
              Abono registrado #{receipt.ledger_entry.id}
            </button>
          ))}
        </div>
      ) : null}
    </section>
  );
}

