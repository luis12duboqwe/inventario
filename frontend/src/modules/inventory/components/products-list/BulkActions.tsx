import React from "react";

type Props = {
  selectedCount: number;
  onActivate?: () => void;
  onDeactivate?: () => void;
  onExport?: () => void;
  onImport?: () => void;
  onMoveCategory?: () => void;
  onTag?: () => void;
  onLabel?: () => void;
  canGenerateLabel?: boolean;
};

export default function BulkActions({
  selectedCount,
  onActivate,
  onDeactivate,
  onExport,
  onImport,
  onMoveCategory,
  onTag,
  onLabel,
  canGenerateLabel = false,
}: Props) {
  if (selectedCount <= 0) {
    return null;
  }

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <div style={{ color: "#94a3b8", fontSize: 13 }}>{selectedCount} seleccionados</div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
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
        {onLabel ? (
          <button
            onClick={onLabel}
            disabled={!canGenerateLabel}
            style={{
              padding: "8px 12px",
              borderRadius: 8,
              background: canGenerateLabel ? "#38bdf8" : "rgba(148, 163, 184, 0.25)",
              color: canGenerateLabel ? "#0f172a" : "#cbd5f5",
              border: 0,
              cursor: canGenerateLabel ? "pointer" : "not-allowed",
              opacity: canGenerateLabel ? 1 : 0.7,
            }}
            title={
              canGenerateLabel
                ? "Generar etiqueta PDF"
                : "Selecciona un solo producto y una sucursal para generar la etiqueta"
            }
          >
            Etiqueta PDF
          </button>
        ) : null}
        <button onClick={onTag} style={{ padding: "8px 12px", borderRadius: 8 }}>
          Etiquetar
        </button>
        <button onClick={onMoveCategory} style={{ padding: "8px 12px", borderRadius: 8 }}>
          Mover categoría
        </button>
        <button onClick={onImport} style={{ padding: "8px 12px", borderRadius: 8 }}>
          Importar
        </button>
        <button
          onClick={onExport}
          style={{ padding: "8px 12px", borderRadius: 8, background: "rgba(255,255,255,0.08)", color: "#e5e7eb", border: 0 }}
        >
          Exportar
        </button>
      </div>
    </div>
  );
}
