import React from "react";

type Props = {
  number?: string;
  status?: string;
  supplierName?: string;
  onReceive?: () => void;
  onInvoice?: () => void;
  onRTV?: () => void;
  onCancel?: () => void;
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

export default function Header({ number, status, supplierName, onReceive, onInvoice, onRTV, onCancel }: Props) {
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
        <button type="button" onClick={onReceive} style={buttonStyle}>
          Recibir
        </button>
        <button type="button" onClick={onInvoice} style={buttonStyle}>
          Registrar factura
        </button>
        <button type="button" onClick={onRTV} style={buttonStyle}>
          Devolución
        </button>
        <button
          type="button"
          onClick={onCancel}
          style={{ ...buttonStyle, background: "#b91c1c", color: "#fff", border: "0" }}
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}
