import React from "react";

type PaymentRowDetails = {
  id: string;
  type: "PAYMENT" | "REFUND" | "CREDIT_NOTE";
  orderId?: string;
  orderNumber?: string;
  customer?: string;
  method?: string;
  amount: number;
  date: string;
  note?: string;
};

type PaymentsSidePanelProps = {
  row?: PaymentRowDetails | null;
  onClose?: () => void;
  onPay?: () => void;
  onRefund?: () => void;
  onCreditNote?: () => void;
};

const currency = new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" });
const dateFormatter = new Intl.DateTimeFormat("es-HN", { dateStyle: "medium", timeStyle: "short" });

function PaymentsSidePanel({
  row,
  onClose,
  onPay,
  onRefund,
  onCreditNote,
}: PaymentsSidePanelProps) {
  if (!row) {
    return null;
  }

  const details: Array<[string, React.ReactNode]> = [
    ["Tipo", row.type],
    ["Pedido", row.orderNumber ?? "—"],
    ["Cliente", row.customer ?? "—"],
    ["Método", row.method ?? "—"],
    ["Monto", currency.format(row.amount ?? 0)],
    ["Fecha", dateFormatter.format(new Date(row.date))],
    ["Notas", row.note ?? "—"],
  ];

  return (
    <aside className="payments-side-panel">
      <div className="payments-side-panel-header">
        <h3 className="payments-side-panel-title">Movimiento</h3>
        <button onClick={onClose} className="payments-side-panel-close-btn">
          Cerrar
        </button>
      </div>

      <div className="payments-side-panel-details">
        {details.map(([label, value]) => (
          <div key={label} className="payments-side-panel-row">
            <span className="payments-side-panel-label">{label}</span>
            <span className="payments-side-panel-value">{value}</span>
          </div>
        ))}
      </div>

      <div className="payments-side-panel-actions">
        <button onClick={onPay} className="payments-side-panel-action-btn">
          Registrar cobro
        </button>
        <button onClick={onRefund} className="payments-side-panel-action-btn">
          Reembolsar
        </button>
        <button onClick={onCreditNote} className="payments-side-panel-action-btn">
          Nota de crédito
        </button>
      </div>
    </aside>
  );
}

export type { PaymentRowDetails, PaymentsSidePanelProps };
export default PaymentsSidePanel;
