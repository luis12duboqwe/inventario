import React from "react";

export type POSActionsProps = {
  onHold?: () => void;
  onResume?: () => void;
  onSaveDraft?: () => void;
  onComplete?: () => void;
  disabled?: boolean;
};

function Actions({ onHold, onResume, onSaveDraft, onComplete, disabled }: POSActionsProps) {
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      <button onClick={onSaveDraft} style={{ padding: "8px 12px", borderRadius: 8 }}>
        Guardar borrador
      </button>
      <button onClick={onHold} style={{ padding: "8px 12px", borderRadius: 8 }}>
        Poner en espera
      </button>
      <button onClick={onResume} style={{ padding: "8px 12px", borderRadius: 8 }}>
        Recuperar ticket
      </button>
      <button
        onClick={onComplete}
        disabled={Boolean(disabled)}
        style={{
          padding: "8px 12px",
          borderRadius: 8,
          background: "#22c55e",
          color: "#0b1220",
          border: 0,
          fontWeight: 700,
          opacity: disabled ? 0.6 : 1,
        }}
      >
        Completar venta
      </button>
    </div>
  );
}

export default Actions;
