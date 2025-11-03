import React from "react";

type Props = {
  number?: string;
  status?: string;
  supplierName?: string;
  onReceive?: () => void;
  onInvoice?: () => void;
  onRTV?: () => void;
  onCancel?: () => void;
  receiveDisabled?: boolean;
  invoiceDisabled?: boolean;
  rtvDisabled?: boolean;
  cancelDisabled?: boolean;
};

const containerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "12px 16px",
  borderRadius: 12,
  background: "rgba(15, 23, 42, 0.8)",
  border: "1px solid rgba(255, 255, 255, 0.08)",
};

const actionsStyle: React.CSSProperties = {
  display: "flex",
  gap: 8,
  flexWrap: "wrap",
  justifyContent: "flex-end",
};

const buttonStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderRadius: 8,
  background: "rgba(37, 99, 235, 0.14)",
  color: "#bfdbfe",
  border: "1px solid rgba(59, 130, 246, 0.4)",
};

export default function Header({
  number,
  status,
  supplierName,
  onReceive,
  onInvoice,
  onRTV,
  onCancel,
  receiveDisabled = false,
  invoiceDisabled = false,
  rtvDisabled = false,
  cancelDisabled = false,
}: Props) {
  const receiveInactive = receiveDisabled || !onReceive;
  const invoiceInactive = invoiceDisabled || !onInvoice;
  const rtvInactive = rtvDisabled || !onRTV;
  const cancelInactive = cancelDisabled || !onCancel;

  return (
    <div style={containerStyle}>
      <div>
        <div style={{ fontSize: 12, color: "#94a3b8" }}>Compra</div>
        <h2 style={{ margin: "4px 0 0 0" }}>{number || "—"}</h2>
        <div style={{ fontSize: 12, color: "#94a3b8" }}>
          {supplierName || "—"} · {status || "DRAFT"}
        </div>
      </div>
      <div style={actionsStyle}>
        <button
          type="button"
          disabled={receiveInactive}
          onClick={receiveInactive ? undefined : onReceive}
          style={{
            ...buttonStyle,
            opacity: receiveInactive ? 0.4 : 1,
            cursor: receiveInactive ? "not-allowed" : "pointer",
          }}
        >
          Recibir
        </button>
        <button
          type="button"
          disabled={invoiceInactive}
          onClick={invoiceInactive ? undefined : onInvoice}
          style={{
            ...buttonStyle,
            opacity: invoiceInactive ? 0.4 : 1,
            cursor: invoiceInactive ? "not-allowed" : "pointer",
          }}
        >
          Registrar factura
        </button>
        <button
          type="button"
          disabled={rtvInactive}
          onClick={rtvInactive ? undefined : onRTV}
          style={{
            ...buttonStyle,
            opacity: rtvInactive ? 0.4 : 1,
            cursor: rtvInactive ? "not-allowed" : "pointer",
          }}
        >
          Devolución
        </button>
        <button
          type="button"
          disabled={cancelInactive}
          onClick={cancelInactive ? undefined : onCancel}
          style={{
            ...buttonStyle,
            background: cancelInactive ? "rgba(185, 28, 28, 0.3)" : "#b91c1c",
            color: "#fff",
            border: cancelInactive ? buttonStyle.border : "0",
            opacity: cancelInactive ? 0.6 : 1,
            cursor: cancelInactive ? "not-allowed" : "pointer",
          }}
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}
