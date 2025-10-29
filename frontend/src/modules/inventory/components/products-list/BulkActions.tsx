import React from "react";

type Props = {
  selectedCount: number;
  onActivate?: () => void;
  onDeactivate?: () => void;
  onExport?: () => void;
  onImport?: () => void;
  onMoveCategory?: () => void;
  onTag?: () => void;
  onAdjustStock?: () => void;
};

export default function BulkActions({
  selectedCount,
  onActivate,
  onDeactivate,
  onExport,
  onImport,
  onMoveCategory,
  onTag,
  onAdjustStock,
}: Props) {
  const hasSelection = selectedCount > 0;

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <div style={{ color: "#94a3b8", fontSize: 13 }}>
        {hasSelection ? `${selectedCount} seleccionados` : "Acciones del catálogo"}
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button onClick={onImport} style={{ padding: "8px 12px", borderRadius: 8 }}>
          Importar
        </button>
        <button
          onClick={onExport}
          style={{ padding: "8px 12px", borderRadius: 8, background: "rgba(255,255,255,0.08)", color: "#e5e7eb", border: 0 }}
        >
          Exportar
        </button>
        {hasSelection && (
          <>
            <button
              onClick={onActivate}
              style={{ padding: "8px 12px", borderRadius: 8, background: "#22c55e", color: "#0b1220", border: 0 }}
            >
              Activar
            </button>
            <button
              onClick={onDeactivate}
              style={{ padding: "8px 12px", borderRadius: 8, background: "#6b7280", color: "#fff", border: 0 }}
            >
              Desactivar
            </button>
            <button onClick={onTag} style={{ padding: "8px 12px", borderRadius: 8 }}>
              Etiquetar
            </button>
            <button onClick={onMoveCategory} style={{ padding: "8px 12px", borderRadius: 8 }}>
              Mover categoría
            </button>
            <button
              onClick={onAdjustStock}
              style={{ padding: "8px 12px", borderRadius: 8, background: "#2563eb", color: "#fff", border: 0 }}
            >
              Ajustar stock
            </button>
          </>
        )}
      </div>
    </div>
  );
}
