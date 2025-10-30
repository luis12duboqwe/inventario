import React from "react";

type Props = {
  onHold?: () => void;
  onPay?: () => void;
  onCancel?: () => void;
  onPrint?: () => void;
  onOffline?: () => void;
};

export default function ActionsBar({ onHold, onPay, onCancel, onPrint, onOffline }: Props) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8 }}>
      <button onClick={onHold} style={{ padding: "10px 12px", borderRadius: 10 }}>
        Guardar
      </button>
      <button
        onClick={onPay}
        style={{
          padding: "10px 12px",
          borderRadius: 10,
          background: "#22c55e",
          color: "#0b1220",
          border: 0,
        }}
      >
        Cobrar
      </button>
      <button onClick={onPrint} style={{ padding: "10px 12px", borderRadius: 10 }}>
        Imprimir
      </button>
      <button onClick={onOffline} style={{ padding: "10px 12px", borderRadius: 10 }}>
        Offline
      </button>
      <button
        onClick={onCancel}
        style={{
          padding: "10px 12px",
          borderRadius: 10,
          background: "#b91c1c",
          color: "#fff",
          border: 0,
        }}
      >
        Cancelar
      </button>
    </div>
  );
}
