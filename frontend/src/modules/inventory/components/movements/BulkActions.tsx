import React from "react";

type Props = {
  selectedCount: number;
  onExport?: () => void;
  onDelete?: () => void;
};

export default function BulkActions({ selectedCount, onExport, onDelete }: Props) {
  if (selectedCount <= 0) return null;
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center", justifyContent: "space-between" }}>
      <div style={{ color: "#94a3b8", fontSize: 13 }}>{selectedCount} seleccionados</div>
      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={onExport}
          style={{ padding: "8px 12px", borderRadius: 8, background: "rgba(255,255,255,0.08)", color: "#e5e7eb", border: 0 }}
        >
          Exportar
        </button>
        <button
          onClick={onDelete}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#b91c1c", color: "#fff", border: 0 }}
        >
          Eliminar
        </button>
      </div>
    </div>
  );
}
