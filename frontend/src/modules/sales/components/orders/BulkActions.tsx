import React from "react";

type Props = {
  selectedCount: number;
  onExport?: () => void;
  onEmail?: () => void;
  onCancel?: () => void;
  onRefund?: () => void;
};

function BulkActions({ selectedCount, onExport, onEmail, onCancel, onRefund }: Props) {
  if (selectedCount <= 0) {
    return null;
  }

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <div style={{ color: "#94a3b8", fontSize: 13 }}>{selectedCount} seleccionadas</div>
      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={onExport}
          style={{
            padding: "8px 12px",
            borderRadius: 8,
            background: "rgba(255, 255, 255, 0.08)",
            color: "#e5e7eb",
            border: 0,
          }}
        >
          Exportar
        </button>
        <button onClick={onEmail} style={{ padding: "8px 12px", borderRadius: 8 }}>
          Enviar factura
        </button>
        <button
          onClick={onCancel}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#b91c1c", color: "#fff", border: 0 }}
        >
          Cancelar
        </button>
        <button
          onClick={onRefund}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#f59e0b", color: "#0b1220", border: 0 }}
        >
          Reembolsar
        </button>
      </div>
    </div>
  );
}

export default BulkActions;
