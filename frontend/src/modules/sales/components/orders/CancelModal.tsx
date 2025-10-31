import React from "react";

type Props = {
  open?: boolean;
  onClose?: () => void;
  onConfirm?: () => void;
};

function CancelModal({ open, onClose, onConfirm }: Props) {
  if (!open) {
    return null;
  }

  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0, 0, 0, 0.5)", display: "grid", placeItems: "center" }}
    >
      <div
        style={{
          width: 420,
          background: "#0b1220",
          borderRadius: 12,
          border: "1px solid rgba(255, 255, 255, 0.08)",
          padding: 16,
        }}
      >
        <h3 style={{ marginTop: 0 }}>Cancelar órdenes</h3>
        <p>¿Seguro que deseas cancelar las órdenes seleccionadas?</p>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
          <button onClick={onClose} style={{ padding: "8px 12px", borderRadius: 8 }}>
            No
          </button>
          <button
            onClick={onConfirm}
            style={{ padding: "8px 12px", borderRadius: 8, background: "#b91c1c", color: "#fff", border: 0 }}
          >
            Sí, cancelar
          </button>
        </div>
      </div>
    </div>
  );
}

export default CancelModal;
