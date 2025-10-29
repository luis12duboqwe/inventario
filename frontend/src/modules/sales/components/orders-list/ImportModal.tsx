import React from "react";

export type OrdersImportModalProps = {
  open?: boolean;
  onClose?: () => void;
};

function ImportModal({ open, onClose }: OrdersImportModalProps) {
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
        <h3 style={{ margin: 0 }}>Importar pedidos (CSV/XLSX)</h3>
        <input type="file" accept=".csv,.xlsx" style={{ padding: 8, borderRadius: 8 }} />
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button onClick={onClose} style={{ padding: "8px 12px", borderRadius: 8 }}>
            Cancelar
          </button>
          <button
            style={{ padding: "8px 12px", borderRadius: 8, background: "#2563eb", color: "#fff", border: 0 }}
            type="button"
          >
            Subir
          </button>
        </div>
      </div>
    </div>
  );
}

export default ImportModal;
