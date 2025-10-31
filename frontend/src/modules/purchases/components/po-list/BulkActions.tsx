import React from "react";

type Props = {
  selectedCount: number;
  onImport?: () => void;
  onExport?: () => void;
  onCancel?: () => void;
  onReceive?: () => void;
};

export default function BulkActions({
  selectedCount,
  onImport,
  onExport,
  onCancel,
  onReceive,
}: Props) {
  if (selectedCount <= 0) {
    return null;
  }

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <div style={{ color: "#94a3b8", fontSize: 13 }}>{selectedCount} seleccionadas</div>
      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={onImport} style={{ padding: "8px 12px", borderRadius: 8 }}>
          Importar
        </button>
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
        <button
          onClick={onReceive}
          style={{
            padding: "8px 12px",
            borderRadius: 8,
            background: "#22c55e",
            color: "#0b1220",
            border: 0,
            fontWeight: 700,
          }}
        >
          Recepcionar
        </button>
        <button
          onClick={onCancel}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#b91c1c", color: "#fff", border: 0 }}
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}
