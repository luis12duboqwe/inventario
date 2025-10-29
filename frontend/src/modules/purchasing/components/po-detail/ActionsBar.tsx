import React from "react";

type Props = {
  onReceive?: () => void;
  onInvoice?: () => void;
  onRTV?: () => void;
  onCancel?: () => void;
};

const containerStyle: React.CSSProperties = {
  display: "flex",
  gap: 8,
  flexWrap: "wrap",
};

const buttonStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderRadius: 8,
  background: "rgba(37, 99, 235, 0.14)",
  color: "#bfdbfe",
  border: "1px solid rgba(59, 130, 246, 0.4)",
};

export default function ActionsBar({ onReceive, onInvoice, onRTV, onCancel }: Props) {
  return (
    <div style={containerStyle}>
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
  );
}
