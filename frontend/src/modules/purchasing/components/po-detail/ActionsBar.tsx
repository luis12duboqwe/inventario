import React from "react";

type Props = {
  onReceive?: () => void;
  onInvoice?: () => void;
  onRTV?: () => void;
  onCancel?: () => void;
  onSend?: () => void;
  onChangeStatus?: () => void;
  receiveDisabled?: boolean;
  invoiceDisabled?: boolean;
  rtvDisabled?: boolean;
  cancelDisabled?: boolean;
  sendDisabled?: boolean;
  statusDisabled?: boolean;
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

export default function ActionsBar({
  onReceive,
  onInvoice,
  onRTV,
  onCancel,
  onSend,
  onChangeStatus,
  receiveDisabled = false,
  invoiceDisabled = false,
  rtvDisabled = false,
  cancelDisabled = false,
  sendDisabled = false,
  statusDisabled = false,
}: Props) {
  const receiveInactive = receiveDisabled || !onReceive;
  const invoiceInactive = invoiceDisabled || !onInvoice;
  const rtvInactive = rtvDisabled || !onRTV;
  const cancelInactive = cancelDisabled || !onCancel;
  const sendInactive = sendDisabled || !onSend;
  const statusInactive = statusDisabled || !onChangeStatus;

  return (
    <div style={containerStyle}>
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
        disabled={statusInactive}
        onClick={statusInactive ? undefined : onChangeStatus}
        style={{
          ...buttonStyle,
          opacity: statusInactive ? 0.4 : 1,
          cursor: statusInactive ? "not-allowed" : "pointer",
        }}
      >
        Actualizar estado
      </button>
      <button
        type="button"
        disabled={sendInactive}
        onClick={sendInactive ? undefined : onSend}
        style={{
          ...buttonStyle,
          opacity: sendInactive ? 0.4 : 1,
          cursor: sendInactive ? "not-allowed" : "pointer",
        }}
      >
        Enviar por correo
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
  );
}
