import React from "react";

import OrdersPaymentStatusBadge from "../orders-list/PaymentStatusBadge";
import OrdersStatusBadge from "../orders-list/StatusBadge";

export type OrderHeaderProps = {
  number?: string;
  status: string;
  paymentStatus: string;
  onPrint?: () => void;
  onExportPDF?: () => void;
  onCancel?: () => void;
  onMarkPaid?: () => void;
};

function Header({ number, status, paymentStatus, onPrint, onExportPDF, onCancel, onMarkPaid }: OrderHeaderProps) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <div style={{ display: "grid", gap: 6 }}>
        <div style={{ fontSize: 12, color: "#94a3b8" }}>Pedido</div>
        <h2 style={{ margin: 0 }}>{number ?? "—"}</h2>
        <div style={{ display: "flex", gap: 8 }}>
          <OrdersPaymentStatusBadge value={paymentStatus} />
          <OrdersStatusBadge value={status} />
        </div>
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button
          onClick={onMarkPaid}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#22c55e", color: "#0b1220", border: 0 }}
        >
          Marcar pagado
        </button>
        <button
          onClick={onCancel}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#b91c1c", color: "#fff", border: 0 }}
        >
          Cancelar
        </button>
        <button onClick={onPrint} style={{ padding: "8px 12px", borderRadius: 8 }}>
          Imprimir
        </button>
        <button onClick={onExportPDF} style={{ padding: "8px 12px", borderRadius: 8 }}>
          PDF
        </button>
      </div>
    </div>
  );
}

export default Header;
