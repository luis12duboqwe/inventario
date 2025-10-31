import React from "react";

type Props = {
  open?: boolean;
  onClose?: () => void;
};

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0, 0, 0, 0.5)",
  display: "grid",
  placeItems: "center",
  zIndex: 40,
};

const modalStyle: React.CSSProperties = {
  width: 520,
  background: "#0b1220",
  borderRadius: 12,
  border: "1px solid rgba(255, 255, 255, 0.08)",
  padding: 16,
  boxShadow: "0 18px 40px rgba(15, 23, 42, 0.6)",
};

const buttonStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderRadius: 8,
  border: "1px solid rgba(59, 130, 246, 0.4)",
  background: "rgba(37, 99, 235, 0.18)",
  color: "#bfdbfe",
};

export default function ExportModal({ open, onClose }: Props) {
  if (!open) {
    return null;
  }

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <h3 style={{ marginTop: 0 }}>Exportar compras</h3>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
          <button type="button" onClick={onClose} style={buttonStyle}>
            Cerrar
          </button>
          <button
            type="button"
            style={{ ...buttonStyle, background: "#2563eb", color: "#fff", border: "0" }}
          >
            Exportar
          </button>
        </div>
      </div>
    </div>
  );
}
