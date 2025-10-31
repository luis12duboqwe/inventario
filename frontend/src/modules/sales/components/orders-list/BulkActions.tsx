import React from "react";

export type OrdersBulkActionsProps = {
  selectedCount: number;
  onMarkPaid?: () => void;
  onCancel?: () => void;
  onExport?: () => void;
  onPrint?: () => void;
  onImport?: () => void;
};

function BulkActions({
  selectedCount,
  onMarkPaid,
  onCancel,
  onExport,
  onPrint,
  onImport,
}: OrdersBulkActionsProps) {
  if (selectedCount <= 0) {
    return null;
  }

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <span style={{ color: "#94a3b8", fontSize: 13 }}>{selectedCount} seleccionados</span>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button
          onClick={onMarkPaid}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#22c55e", color: "#0b1220", border: 0 }}
        >
          Marcar pagado
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
          style={{ padding: "8px 12px", borderRadius: 8, background: "rgba(255, 255, 255, 0.08)", color: "#e5e7eb", border: 0 }}
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

export default BulkActions;
