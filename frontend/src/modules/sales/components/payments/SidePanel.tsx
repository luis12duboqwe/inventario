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

const currency = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });
const dateFormatter = new Intl.DateTimeFormat("es-MX", { dateStyle: "medium", timeStyle: "short" });

function PaymentsSidePanel({ row, onClose, onPay, onRefund, onCreditNote }: PaymentsSidePanelProps) {
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
    <aside
      style={{
        position: "fixed",
        right: 0,
        top: 0,
        bottom: 0,
        width: 420,
        background: "#0b1220",
        borderLeft: "1px solid rgba(148, 163, 184, 0.2)",
        padding: 16,
        overflowY: "auto",
        zIndex: 40,
        boxShadow: "-12px 0 32px rgba(15, 23, 42, 0.45)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h3 style={{ margin: 0 }}>Movimiento</h3>
        <button onClick={onClose} style={{ padding: "6px 10px", borderRadius: 8 }}>Cerrar</button>
      </div>

      <div style={{ display: "grid", gap: 8 }}>
        {details.map(([label, value]) => (
          <div
            key={label}
            style={{
              display: "flex",
              justifyContent: "space-between",
              borderBottom: "1px dashed rgba(148, 163, 184, 0.2)",
              padding: "6px 0",
              fontSize: 14,
            }}
          >
            <span style={{ color: "#94a3b8" }}>{label}</span>
            <span style={{ marginLeft: 16, textAlign: "right" }}>{value}</span>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
        <button onClick={onPay} style={{ padding: "8px 12px", borderRadius: 8 }}>Registrar cobro</button>
        <button onClick={onRefund} style={{ padding: "8px 12px", borderRadius: 8 }}>Reembolsar</button>
        <button onClick={onCreditNote} style={{ padding: "8px 12px", borderRadius: 8 }}>Nota de crédito</button>
      </div>
    </aside>
  );
}

export type { PaymentRowDetails, PaymentsSidePanelProps };
export default PaymentsSidePanel;
