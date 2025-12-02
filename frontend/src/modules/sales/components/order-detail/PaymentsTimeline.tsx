import React from "react";

type Payment = {
  id: string;
  date: string;
  amount: number;
  method: string;
  note?: string;
};

type Props = {
  items?: Payment[];
};

function PaymentsTimeline({ items }: Props) {
  const data = Array.isArray(items) ? items : [];

  return (
    <div className="order-payments-timeline-card">
      <div className="order-payments-timeline-label">Pagos</div>
      {data.length === 0 ? (
        <div className="order-payments-timeline-empty">Sin pagos</div>
      ) : (
        <div className="order-payments-timeline-list">
          {data.map((payment) => (
            <div key={payment.id} className="order-payments-timeline-item">
              <span>
                {new Date(payment.date).toLocaleString()} — {payment.method}
                {payment.note ? ` · ${payment.note}` : ""}
              </span>
              <span>{Intl.NumberFormat().format(payment.amount)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default PaymentsTimeline;
