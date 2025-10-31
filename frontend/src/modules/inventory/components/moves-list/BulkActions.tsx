import React from "react";

type Props = {
  selectedCount: number;
  onApprove?: () => void;
  onCancel?: () => void;
  onExport?: () => void;
  onPrint?: () => void;
  onImport?: () => void;
};

export default function BulkActions({
  selectedCount,
  onApprove,
  onCancel,
  onExport,
  onPrint,
  onImport,
}: Props) {
  if (selectedCount <= 0) {
    return null;
  }

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <div style={{ color: "#94a3b8", fontSize: 13 }}>{selectedCount} seleccionados</div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button
          onClick={onApprove}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#22c55e", color: "#0b1220", border: 0 }}
        >
          Aprobar
        </button>
        <button
          onClick={onCancel}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#b91c1c", color: "#fff", border: 0 }}
        >
          Cancelar
        </button>
        <button onClick={onImport} style={{ padding: "8px 12px", borderRadius: 8 }}>
          Importar
        </button>
        <button
          onClick={onExport}
          style={{
            padding: "8px 12px",
            borderRadius: 8,
            background: "rgba(255,255,255,0.08)",
            color: "#e5e7eb",
            border: 0,
          }}
        >
          Exportar
        </button>
        <button onClick={onPrint} style={{ padding: "8px 12px", borderRadius: 8 }}>
          Imprimir
        </button>
      </div>
    </div>
  );
}
