import React from "react";

import OrderStatusBadge from "../orders/StatusBadge";

type Props = {
  orderNumber?: string;
  status: string;
  onPrint?: () => void;
  onEmail?: () => void;
  onCapturePayment?: () => void;
  onCancel?: () => void;
};

function Header({ orderNumber, status, onPrint, onEmail, onCapturePayment, onCancel }: Props) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <div>
        <div style={{ fontSize: 12, color: "#94a3b8" }}>Factura</div>
        <h2 style={{ margin: "4px 0 0 0" }}>{orderNumber || "—"}</h2>
        <div style={{ marginTop: 6 }}>
          <OrderStatusBadge value={status} />
        </div>
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={onPrint} style={{ padding: "8px 12px", borderRadius: 8 }}>
          Imprimir
        </button>
        <button onClick={onEmail} style={{ padding: "8px 12px", borderRadius: 8 }}>
          Enviar
        </button>
        <button
          onClick={onCapturePayment}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#22c55e", color: "#0b1220", border: 0, fontWeight: 700 }}
        >
          Registrar pago
        </button>
        <button
          onClick={onCancel}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#b91c1c", color: "#fff", border: 0 }}
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}

export default Header;
