import React from "react";

export type OrdersExportModalProps = {
  open?: boolean;
  onClose?: () => void;
};

function ExportModal({ open, onClose }: OrdersExportModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(15, 23, 42, 0.72)",
        display: "grid",
        placeItems: "center",
        zIndex: 60,
      }}
    >
      <div
        style={{
          width: 520,
          background: "#0b1220",
          borderRadius: 12,
          border: "1px solid rgba(255, 255, 255, 0.08)",
          padding: 16,
          display: "grid",
          gap: 12,
        }}
      >
        <h3 style={{ margin: 0 }}>Exportar pedidos</h3>
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button onClick={onClose} style={{ padding: "8px 12px", borderRadius: 8 }}>
            Cerrar
          </button>
          <button
            style={{ padding: "8px 12px", borderRadius: 8, background: "#2563eb", color: "#fff", border: 0 }}
            type="button"
          >
            Exportar
          </button>
        </div>
      </div>
    </div>
  );
}

export default ExportModal;
