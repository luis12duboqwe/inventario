import React from "react";

export type POSLineEditorValue = {
  id: string;
  qty: number;
  discountPct?: number;
  note?: string;
};

export type POSLineEditorProps = {
  line?: POSLineEditorValue | null;
  onPatch: (patch: Partial<POSLineEditorValue>) => void;
};

function LineEditor({ line, onPatch }: POSLineEditorProps) {
  if (!line) {
    return null;
  }

  return (
    <div style={{ display: "grid", gap: 8, border: "1px solid rgba(255, 255, 255, 0.08)", borderRadius: 8, padding: 8 }}>
      <span style={{ fontSize: 12, color: "#94a3b8" }}>Editar línea</span>
      <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span>Cantidad</span>
        <input
          type="number"
          min={0}
          value={line.qty}
          onChange={(event) => onPatch({ qty: Number(event.target.value || 0) })}
          style={{ width: 100, padding: 6, borderRadius: 8 }}
        />
      </label>
      <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span>Desc. %</span>
        <input
          type="number"
          min={0}
          value={line.discountPct ?? 0}
          onChange={(event) => onPatch({ discountPct: Number(event.target.value || 0) })}
          style={{ width: 100, padding: 6, borderRadius: 8 }}
        />
      </label>
      <textarea
        placeholder="Nota"
        value={line.note ?? ""}
        onChange={(event) => onPatch({ note: event.target.value })}
        style={{ padding: 8, borderRadius: 8, minHeight: 72 }}
      />
    </div>
  );
}

export default LineEditor;
