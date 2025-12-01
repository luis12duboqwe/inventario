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
    <div className="pos-line-editor">
      <span className="pos-line-editor-title">Editar línea</span>
      <label className="pos-line-editor-field">
        <span>Cantidad</span>
        <input
          type="number"
          min={0}
          value={line.qty}
          onChange={(event) => onPatch({ qty: Number(event.target.value || 0) })}
          className="pos-line-editor-input"
        />
      </label>
      <label className="pos-line-editor-field">
        <span>Desc. %</span>
        <input
          type="number"
          min={0}
          value={line.discountPct ?? 0}
          onChange={(event) => onPatch({ discountPct: Number(event.target.value || 0) })}
          className="pos-line-editor-input"
        />
      </label>
      <textarea
        placeholder="Nota"
        value={line.note ?? ""}
        onChange={(event) => onPatch({ note: event.target.value })}
        className="pos-line-editor-textarea"
      />
    </div>
  );
}

export default LineEditor;
