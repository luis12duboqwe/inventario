import React from "react";

type Props = {
  open?: boolean;
  onClose?: () => void;
};

export default function ImportModal({ open, onClose }: Props) {
  if (!open) return null;
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.5)",
        display: "grid",
        placeItems: "center",
        zIndex: 50,
      }}
    >
      <div
        style={{
          width: 560,
          maxWidth: "95vw",
          background: "#0b1220",
          borderRadius: 12,
          border: "1px solid rgba(255,255,255,0.08)",
          padding: 16,
        }}
      >
        <h3 style={{ marginTop: 0 }}>Importar productos</h3>
        {/* Dropzone y validador (se conectará en pack posterior) */}
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
          <button onClick={onClose} style={{ padding: "8px 12px", borderRadius: 8 }}>
            Cerrar
          </button>
          <button
            style={{ padding: "8px 12px", borderRadius: 8, background: "#2563eb", color: "#fff", border: 0 }}
          >
            Procesar
          </button>
        </div>
      </div>
    </div>
  );
}
