import React from "react";

type Props = {
  selectedCount: number;
  onExport?: () => void;
  onImport?: () => void;
};

const containerStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  padding: "8px 12px",
  borderRadius: 12,
  background: "rgba(15, 23, 42, 0.7)",
  border: "1px solid rgba(148, 163, 184, 0.2)",
};

const buttonStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderRadius: 8,
  border: "1px solid rgba(255, 255, 255, 0.08)",
  background: "rgba(37, 99, 235, 0.1)",
  color: "#93c5fd",
};

export default function BulkActions({ selectedCount, onExport, onImport }: Props) {
  if (selectedCount <= 0) {
    return null;
  }

  return (
    <div style={containerStyle}>
      <div style={{ color: "#94a3b8", fontSize: 13 }}>{selectedCount} seleccionadas</div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button type="button" onClick={onImport} style={buttonStyle}>
          Importar
        </button>
        <button
          type="button"
          onClick={onExport}
          style={{ ...buttonStyle, background: "rgba(255, 255, 255, 0.08)", color: "#e5e7eb" }}
        >
          Exportar
        </button>
      </div>
    </div>
  );
}
